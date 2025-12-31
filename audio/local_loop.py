
import asyncio
import time
import queue
import logging
import numpy as np
import pyaudio
import struct
import math
import io
import threading
import re

from core.colors import Colors
from core.connection import get_connection_manager
from tools.llm.router import get_llm_router
from tools.audio.stt import OfflineSTT
from tools.audio.tts import OfflineTTS
from core.offline import OfflineTools, get_tool_response

# Vision support imports
try:
    from PIL import ImageGrab  # Screen capture
    SCREEN_CAPTURE_AVAILABLE = True
except ImportError:
    SCREEN_CAPTURE_AVAILABLE = False

try:
    import cv2  # Camera capture
    CAMERA_AVAILABLE = True
except ImportError:
    CAMERA_AVAILABLE = False

# Constants
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
VAD_THRESHOLD = 500  # Silence threshold
SILENCE_DURATION = 1.5  # Seconds to wait before processing

logger = logging.getLogger("atomik.audio.local")

class LocalAudioLoop:
    def __init__(self):
        self.pya = pyaudio.PyAudio()
        self.stt = None
        self.tts = None
        self.router = get_llm_router()
        self.connection = get_connection_manager()
        
        self.is_running = False
        self.mic_queue = queue.Queue()
        
        # State
        self.is_speaking = False
        self.silence_start = None
        self.audio_buffer = []
        self.chat_history = []
        self.offline_tools = OfflineTools()  # Local tools (files, reminders, etc.)
        self.offline_prompt = None
        self.last_response = "" # Store last LLM response for copying
        self.vision_prompt_content = None # Cache for vision prompt

    async def initialize(self):
        """Lazy load models"""
        print(f"{Colors.YELLOW}Offline Ses Modülleri Yükleniyor... (Biraz sürebilir){Colors.RESET}")
        
        # Load STT
        if not self.stt:
             print(f"{Colors.DIM}Whisper yükleniyor...{Colors.RESET}")
             # Run in thread to not block event loop
             self.stt = await asyncio.to_thread(OfflineSTT)
             
        # Load TTS
        if not self.tts:
             print(f"{Colors.DIM}Piper TTS yükleniyor...{Colors.RESET}")
             # Check for ref file
             ref_path = "tools/audio/reference_voice.wav"
             self.tts = await asyncio.to_thread(OfflineTTS, ref_path)

        if self.stt and self.stt.model:
            print(f"{Colors.GREEN}Offline Modüller Hazır!{Colors.RESET}")
            
            # Preload system prompt (User request)
            print(f"{Colors.DIM}Sistem beyni hazırlanıyor...{Colors.RESET}")
            try:
                # Force load prompt into memory
                self.offline_prompt = self.router._get_system_prompt("core", force_offline=True)
            except Exception as e:
                logger.error(f"Prompt preload error: {e}")

            # Preload vision prompt
            try:
                with open("/home/atom13/Projeler/Atomik/AtomBase/prompts/offline/vision_offline.txt", "r", encoding="utf-8") as f:
                    self.vision_prompt_content = f.read()
                print(f"{Colors.DIM}INFO | Loaded vision prompt: vision_offline.txt{Colors.RESET}")
            except Exception as e:
                self.vision_prompt_content = "Görüntüyü analiz et."
                logger.warning(f"Vision prompt load warning: {e}")

            # Say hello to user
            greeting = "Merhaba! Offline Mod. Cevaplar kötü olabilir."
            if self.tts:
                await asyncio.to_thread(self.tts.speak, greeting)

            # Start proactive loop
            asyncio.create_task(self.proactive_notification_loop())
        else:
            print(f"{Colors.RED}Offline STT Modeli yüklenemedi (İnternet yok ve önbellek boş).{Colors.RESET}")

    def capture_screen(self):
        """Capture screen for vision analysis"""
        if not SCREEN_CAPTURE_AVAILABLE:
            return None, "Ekran yakalama için Pillow gerekli (pip install Pillow)"
        
        try:
            screenshot = ImageGrab.grab()
            # Convert to bytes
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            return buffer.getvalue(), None
        except Exception as e:
            return None, f"Ekran yakalama hatası: {e}"

    def capture_camera(self):
        """Capture from webcam for vision analysis"""
        if not CAMERA_AVAILABLE:
            return None, "Kamera için opencv gerekli (pip install opencv-python)"
        
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return None, "Kamera açılamadı"
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                return None, "Kamera görüntüsü alınamadı"
            
            # Convert BGR to RGB and encode as PNG
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            from PIL import Image
            img = Image.fromarray(frame_rgb)
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue(), None
        except Exception as e:
            return None, f"Kamera hatası: {e}"

    async def handle_vision_request(self, text, mode="screen"):
        """Handle vision-based requests"""
        print(f"{Colors.CYAN}📸 Görsel yakalama ({mode})...{Colors.RESET}")
        
        # Capture image
        if mode == "camera" or mode == "kamera":
            image_bytes, error = self.capture_camera()
        else:
            image_bytes, error = self.capture_screen()
        
        if error:
            return f"Görüntü yakalanamadı: {error}"
        
        # Use vision model via OllamaClient directly
        from tools.llm.ollama_client import OllamaClient
        vision_client = OllamaClient()
        
        # Use cached vision prompt
        vision_system_prompt = self.vision_prompt_content
        if not vision_system_prompt:
             vision_system_prompt = "Görüntüyü analiz et."

        # Create prompt with user's question
        if not text: text = "Gördüğünü anlat."
        vision_prompt = f"{vision_system_prompt}\n\nKullanıcı sorusu: {text}\n(Lütfen sistem promptundaki kurallara göre analiz yap)"
        
        print(f"{Colors.DIM}🔍 Görsel analiz ediliyor...{Colors.RESET}")
        result = await asyncio.to_thread(
            vision_client.analyze_image,
            image_bytes=image_bytes,
            prompt=vision_prompt
        )
        
        return result


    async def listen_mic(self):
        """Microphone capture loop"""
        # Find reliable input device
        input_device_index = None
        for i in range(self.pya.get_device_count()):
            try:
                info = self.pya.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    # Test opening stream
                    stream = self.pya.open(
                        format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,
                        input_device_index=i, frames_per_buffer=CHUNK
                    )
                    stream.close()
                    input_device_index = i
                    if "pulse" in info['name'].lower():
                        break
            except Exception:
                continue
        
        if input_device_index is None:
             print(f"{Colors.RED}❌ Mikrofon bulunamadı!{Colors.RESET}")
             return

        stream = self.pya.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            input_device_index=input_device_index,
            frames_per_buffer=CHUNK
        )
        
        print(f"{Colors.CYAN}Dinliyorum... (Konuşmanız bitince otomatik algılar){Colors.RESET}")
        
        while self.is_running:
            try:
                data = await asyncio.to_thread(stream.read, CHUNK, exception_on_overflow=False)
                self.mic_queue.put(data)
                
                # VAD & Buffer Logic
                # Convert to numpy for analysis
                # (Simple energy based VAD)
                shorts = struct.unpack(f"<{len(data)//2}h", data)
                rms = math.sqrt(sum(s**2 for s in shorts) / len(shorts))
                
                if rms > VAD_THRESHOLD:
                    self.is_speaking = True
                    self.silence_start = None
                    self.audio_buffer.append(data)
                else:
                    if self.is_speaking:
                        self.audio_buffer.append(data) # Keep recording silence briefly
                        if self.silence_start is None:
                            self.silence_start = time.time()
                        elif time.time() - self.silence_start > SILENCE_DURATION:
                            # Speech finished, process buffer
                            self.is_speaking = False
                            await self.process_speech()
                            self.audio_buffer = [] # Reset buffer
                            self.silence_start = None
                            print(f"{Colors.CYAN}Dinliyorum...{Colors.RESET}")
            
            except Exception as e:
                logger.error(f"Mic error: {e}")
                await asyncio.sleep(0.1)

    async def process_speech(self):
        """Process recorded speech buffer"""
        if not self.audio_buffer:
            return
            
        # Merge buffer
        full_audio = b''.join(self.audio_buffer)
        
        # Convert buffer to float32 numpy for Whisper
        audio_np = np.frombuffer(full_audio, dtype=np.int16).astype(np.float32) / 32768.0

        # 1. STT Transcribe
        cursor = "..."
        print(f"{Colors.GREEN}[Sen] {cursor}{Colors.RESET}", end="\r")
        text = await asyncio.to_thread(self.stt.transcribe, audio_np)
        
        if not text.strip():
            # Noise detected but no speech
            return
            
        print(f"{Colors.GREEN}[Sen] {text}{Colors.RESET}   ")
        await self.generate_and_respond(text)

    async def text_input_loop(self):
        """Fallback text input loop when STT is not available"""
        print(f"\n{Colors.YELLOW}Ses algılama çalışmadığı için KLAVYE moduna geçildi.{Colors.RESET}")
        print(f"{Colors.DIM}Çıkmak için 'q' veya 'exit' yazın.{Colors.RESET}\n")
        
        while self.is_running:
            try:
                text = await asyncio.to_thread(input, f"{Colors.GREEN}[Sen] {Colors.RESET}")
                text = text.strip()
                if not text:
                    continue
                if text.lower() in ['q', 'exit', 'çık']:
                    self.stop()
                    break
                
                await self.generate_and_respond(text)
                
            except (EOFError, KeyboardInterrupt):
                self.stop()
                break

    async def generate_and_respond(self, text, is_vision_request=False):
        """Handle LLM response with streaming and history"""
        text_lower = text.lower()
        
        # Vision keyword check (if not already triggered)
        vision_mode = "screen"
        vision_keywords_camera = ["kameraya bak", "kamerayı aç", "beni gör", "bana bak", "kamera", "fotoğraf"]
        vision_keywords_screen = ["ekrana bak", "ekranı oku", "göster", "ekran"]
        
        # Check for copy command suffix "ve kopyala"
        should_copy = False
        # Match: "şunu yap ve kopyala" or "... ve panoya kopyala"
        copy_match = re.search(r'(.*?)\s+(?:ve|sonra)\s+(?:panoya\s+)?(?:bunu\s+)?kopyala[.!]?$', text, re.IGNORECASE)
        if copy_match:
            text = copy_match.group(1).strip()
            should_copy = True
            print(f"{Colors.YELLOW}📋 Otomatik kopyalama aktif.{Colors.RESET}")
            
        # Standalone copy command
        if text.lower() in ["kopyala", "bunu kopyala", "panoya kopyala", "cevabı kopyala"]:
            if self.last_response:
                msg = self.offline_tools.copy_to_clipboard(self.last_response)
                print(f"{Colors.GREEN}📋 {msg}{Colors.RESET}")
                if self.tts: self.tts.speak("Kopyaladım.")
            else:
                print("Kopyalanacak cevap yok.")
            return
        
        if not is_vision_request:
            for keyword in vision_keywords_camera:
                if keyword in text_lower:
                    is_vision_request = True
                    vision_mode = "camera"
                    break
        
        if not is_vision_request:
            for keyword in vision_keywords_screen:
                if keyword in text_lower:
                    is_vision_request = True
                    vision_mode = "screen"
                    break
        
        # Handle vision request
        if is_vision_request:
            print(f"{Colors.GREEN}Atomik (Vision): {Colors.RESET}", end="", flush=True)
            response_text = await self.handle_vision_request(text, mode=vision_mode)
            print(response_text)
            
            self.chat_history.append({"role": "user", "content": text})
            self.chat_history.append({"role": "assistant", "content": response_text})
            self.last_response = response_text # Store last response
            
            if should_copy:
                self.offline_tools.copy_to_clipboard(response_text)
                print(f"{Colors.YELLOW}📋 Cevap panoya kopyalandı.{Colors.RESET}")

            if self.tts:
                await asyncio.to_thread(self.tts.speak, response_text[:200])
            print(f"Dinliyorum...")

            
            # CHAINING: Vision -> Tool
            # Eğer kullanıcı "dosyaya kaydet" dediyse akışı kesme, içeriği ekle
            chain_keywords = ["dosya", "kaydet", "not", "belge", "yaz"]
            if any(kw in text.lower() for kw in chain_keywords):
                print(f"{Colors.YELLOW}🔗 Vision -> Tool zinciri aktif.{Colors.RESET}")
                # Inject vision content so regex tools can find it
                # "İçerik:" prefix matches one of the regex patterns in offline_tools.py
                text += f"\nİçerik: {response_text}"
            else:
                return
        
        # Check for offline tool commands
        tool_used, tool_response = get_tool_response(text, self.offline_tools)
        if tool_used:
            print(f"{Colors.GREEN}Atomik (Tool): {tool_response}{Colors.RESET}")
            if self.tts:
                await asyncio.to_thread(self.tts.speak, tool_response[:150])
            
            # Add to history to keep context of files etc
            self.chat_history.append({"role": "user", "content": text})
            self.chat_history.append({"role": "assistant", "content": tool_response})
            self.last_response = tool_response # Store last response
            
            if should_copy:
                self.offline_tools.copy_to_clipboard(tool_response)
                print(f"{Colors.YELLOW}📋 Cevap panoya kopyalandı.{Colors.RESET}")

            print(f"Dinliyorum...")
            return
        
        # Keep history
        self.chat_history.append({"role": "user", "content": text})
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]
        
        # Build prompt
        prompt_parts = []
        for msg in self.chat_history:
            role = "Kullanıcı" if msg["role"] == "user" else "Atomik"
            prompt_parts.append(f"{role}: {msg['content']}")
            
        if should_copy:
             # Force raw output for clipboard
             prompt_parts.append("\n(SİSTEM: Kullanıcı bu cevabı KOPYALAYACAK. Sadece istenen metni/kodu yaz. Sohbet cümleleri ekleme. Tırnak içine alma.)")
        
        prompt = "\n".join(prompt_parts) + "\nAtomik:"
        
        # Get offline system prompt (Use cached if avail)
        sys_prompt = self.offline_prompt
        if not sys_prompt:
             sys_prompt = self.router._get_system_prompt("core", force_offline=True)
        
        print(f"{Colors.GREEN}Atomik: {Colors.RESET}", end="", flush=True)
        
        # --- STREAMING LOOP ---
        full_response = ""
        buffer = ""
        
        loop = asyncio.get_event_loop()
        q = asyncio.Queue()
        
        def producer():
            try:
                # Call Router with stream=True
                generator = self.router.generate_text(
                    prompt, 
                    system_prompt=sys_prompt, 
                    stream=True, 
                    force_offline=True
                )
                
                if isinstance(generator, str): # Error or non-stream
                    loop.call_soon_threadsafe(q.put_nowait, generator)
                    loop.call_soon_threadsafe(q.put_nowait, None)
                    return

                for chunk in generator:
                    if chunk:
                        loop.call_soon_threadsafe(q.put_nowait, chunk)
                loop.call_soon_threadsafe(q.put_nowait, None)
            except Exception as e:
                print(f"Gen error: {e}")
                loop.call_soon_threadsafe(q.put_nowait, None)
        
        # Start generation in thread
        threading.Thread(target=producer, daemon=True).start()
        
        while True:
            chunk = await q.get()
            if chunk is None:
                break
            
            # Print and accumulate
            print(chunk, end="", flush=True)
            full_response += chunk
            buffer += chunk
            
            # Sentence splitting for TTS
            # Split by . ! ? : ; followed by space or newline
            match = re.search(r'([.?!:;])(\s|$)', buffer)
            if match:
                split_idx = match.end()
                sentence = buffer[:split_idx].strip()
                if sentence:
                    # Clean and Speak
                    clean_sent = self._clean_text(sentence)
                    if clean_sent and self.tts:
                        self.tts.speak(clean_sent)
                
                buffer = buffer[split_idx:]
        
        # Speak remaining buffer
        if buffer.strip():
            clean_sent = self._clean_text(buffer)
            if clean_sent and self.tts:
                self.tts.speak(clean_sent)
        
        print() # Newline
        
        # Store for history and clipboard
        self.chat_history.append({"role": "assistant", "content": full_response})
        self.last_response = full_response
        
        if should_copy:
            self.offline_tools.copy_to_clipboard(full_response)
            print(f"{Colors.YELLOW}📋 Cevap panoya kopyalandı.{Colors.RESET}")
        
        # Auto-copy if response says so (e.g. "Panoya kopyaladım")
        elif "kopyaladım" in full_response.lower() or "panoya aldım" in full_response.lower():
             self.offline_tools.copy_to_clipboard(full_response)
             print(f"{Colors.YELLOW}📋 (Oto) Cevap panoya kopyalandı.{Colors.RESET}")
        
        print(f"Dinliyorum...")

    def _clean_text(self, text):
        """Clean text for TTS"""
        # Remove thinking blocks <think>...</think>
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        # Remove markdown
        text = text.replace("**", "").replace("*", "").replace("`", "")
        # Remove emojis (basic)
        return text.strip()

    async def run(self):
        self.is_running = True
        
        # Initialize models
        await self.initialize()
        
        print(f"{Colors.RED}🔴 OFFLINE MOD (Yerel Modeller){Colors.RESET}")
        
        # Check if STT is working
        if self.stt and self.stt.model:
            print("Konuşmaya başlayabilirsiniz...")
            await self.listen_mic()
        else:
            # Fallback to text
            await self.text_input_loop()

    async def proactive_notification_loop(self):
        """Background loop for proactive notifications (reminders)"""
        logger.info("Proaktif döngü başlatıldı.")
        while self.is_running:
            try:
                # Check reminders
                due_reminders = self.offline_tools.check_due_reminders()
                for text in due_reminders:
                    msg = f"Hatırlatma zamanı: {text}"
                    print(f"\n{Colors.MAGENTA}🔔 {msg}{Colors.RESET}")
                    
                    # 1. System Notification (notify-send)
                    try:
                        subprocess.run(["notify-send", "Atomik Hatırlatıcı", text], timeout=1)
                    except:
                        pass
                    
                    # 2. TTS Announcement
                    if self.tts:
                        self.tts.speak(msg)
                
            except Exception as e:
                logger.error(f"Proactive loop error: {e}")
            
            await asyncio.sleep(10) # Check every 10 secs

    def stop(self):
        self.is_running = False
        if self.pya:
            self.pya.terminate()
