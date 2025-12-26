"""
Atomik - Realtime Voice Chat with AtomBase Tool Calling
Based on ada_v2 pattern + AtomBase tools integration
"""
import asyncio
import os
import sys
import traceback
from dotenv import load_dotenv
import pyaudio
from google import genai
from google.genai import types

# Add AtomBase to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AtomBase'))

# Load environment variables
load_dotenv()

# Try AtomBase .env if main one doesn't have the key
if not os.getenv("GEMINI_API_KEY"):
    load_dotenv(os.path.join(os.path.dirname(__file__), 'AtomBase', '.env'))

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("Error: GEMINI_API_KEY not found in .env file.")
    sys.exit(1)

# Audio Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# Model
MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"

# ANSI Colors for TUI  
class Colors:
    RESET = "\033[0m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    DIM = "\033[2m"
    BOLD = "\033[1m"

def print_header():
    os.system('clear' if os.name != 'nt' else 'cls')
    print(f"{Colors.BOLD}{Colors.CYAN}╔══════════════════════════════════════════════════╗{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}║      ATOMIK + AtomBase - Voice Assistant         ║{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}╚══════════════════════════════════════════════════╝{Colors.RESET}")
    print(f"{Colors.DIM}Press Ctrl+C to exit{Colors.RESET}\n")

# ============================================================
# AtomBase Tool Definitions for Gemini Live API
# ============================================================

# Import AtomBase tool functions
try:
    from AtomBase.tools.basic import get_current_time, run_neofetch
    from AtomBase.tools.files import list_files, read_file, write_file, scan_workspace
    from AtomBase.tools.execution import run_terminal_command
    from AtomBase.tools.coding import delegate_coding, save_generated_code
    from AtomBase.tools.memory import (
        save_context, get_context_info, get_memory_stats, clear_memory,
        add_to_history, get_all_context, get_user_name
    )
    from AtomBase.tools.weather import get_weather
    from AtomBase.tools.camera import capture_frame, get_camera_payload
    from AtomBase.tools.visual_memory import (
        save_visual_observation, get_visual_history, 
        compare_with_last, get_visual_context_for_prompt
    )
    ATOMBASE_AVAILABLE = True
    CODING_AVAILABLE = True
    MEMORY_AVAILABLE = True
    WEATHER_AVAILABLE = True
    CAMERA_AVAILABLE = True
    VISUAL_MEMORY_AVAILABLE = True
    print(f"{Colors.GREEN}AtomBase araçları yüklendi!{Colors.RESET}")
except ImportError as e:
    print(f"{Colors.YELLOW}AtomBase araçları yüklenemedi: {e}{Colors.RESET}")
    ATOMBASE_AVAILABLE = False
    CODING_AVAILABLE = False
    MEMORY_AVAILABLE = False
    WEATHER_AVAILABLE = False
    CAMERA_AVAILABLE = False

# Load system prompt from file
def load_system_prompt():
    prompt_file = os.path.join(os.path.dirname(__file__), "AtomBase", "prompts", "supervisor.txt")
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "Sen Atomik, Türkçe konuşan sesli asistansın. Kısa ve öz cevaplar ver."

SYSTEM_PROMPT = load_system_prompt()

# Function declarations for Gemini Live API
TOOL_DECLARATIONS = [
    {
        "name": "get_current_time",
        "description": "Returns the current local time formatted as YYYY-MM-DD HH:MM:SS.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "list_files",
        "description": "Lists files in a directory within the workspace.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "directory": {
                    "type": "STRING",
                    "description": "Directory path relative to workspace (default: '.')"
                }
            }
        }
    },
    {
        "name": "read_file",
        "description": "Reads content from a file in the workspace.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "filename": {
                    "type": "STRING",
                    "description": "Path to the file to read"
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "write_file",
        "description": "Writes content to a file in the workspace. Overwrites if exists.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "filename": {
                    "type": "STRING",
                    "description": "Path to the file to write"
                },
                "content": {
                    "type": "STRING",
                    "description": "Content to write to the file"
                }
            },
            "required": ["filename", "content"]
        }
    },
    {
        "name": "scan_workspace",
        "description": "Scans the workspace and returns a file tree structure.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "max_depth": {
                    "type": "INTEGER",
                    "description": "Maximum directory depth (default: 2)"
                }
            }
        }
    },
    {
        "name": "run_terminal_command",
        "description": "Executes a terminal command in the workspace. Supports: python, pip, git, ls, cat, etc.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "The command to execute"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "run_neofetch",
        "description": "Displays system information with ASCII art using neofetch.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "delegate_coding",
        "description": "Kod yazma isteğini daha akıllı bir modele (Gemini 3 Flash) ilet. Karmaşık kod işleri için kullan. Model optimize edilmiş prompt ile kod üretir ve dosyaya kaydeder.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt": {
                    "type": "STRING",
                    "description": "Kullanıcının kod isteği. Detaylı olmalı."
                },
                "context": {
                    "type": "STRING",
                    "description": "Opsiyonel bağlam bilgisi (mevcut dosyalar, kullanılan teknolojiler vb.)"
                }
            },
            "required": ["prompt"]
        },
        "behavior": "NON_BLOCKING"
    },
    # Memory Tools
    {
        "name": "save_context",
        "description": "Önemli bilgiyi hafızaya kaydet. Örn: proje adı, kullanılan teknoloji.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {"type": "STRING", "description": "Bilgi anahtarı (örn: proje_adi)"},
                "value": {"type": "STRING", "description": "Kaydedilecek değer"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "get_context_info",
        "description": "Hafızadan bilgi getir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {"type": "STRING", "description": "Bilgi anahtarı"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "get_memory_stats",
        "description": "Hafızadaki tüm bilgilerin özetini göster.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "clear_memory",
        "description": "Hafızayı temizle.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    # Weather Tool
    {
        "name": "get_weather",
        "description": "Şehir için hava durumu sorgula.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "Şehir adı (örn: Istanbul, Ankara)"}
            },
            "required": ["city"]
        }
    },
    # Camera Tool
    {
        "name": "capture_frame",
        "description": "Kameradan görüntü al ve görüntüyü analiz et. Görsel soru-cevap için kullan.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    # Exit Tool
    {
        "name": "exit_app",
        "description": "Uygulamadan çık. Kullanıcı 'hoşçakal', 'görüşürüz', 'kapat', 'çık' gibi şeyler söylediğinde kullan.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    # Visual Memory Tools
    {
        "name": "save_visual_observation",
        "description": "Kullanıcının görünümünü kaydet (gözlük, saç, kıyafet vb.). Oturum sonunda veya önemli değişikliklerde kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "notes": {"type": "STRING", "description": "Görsel gözlem notları (örn: 'Siyah gözlüklü, beyaz tişört')"}
            },
            "required": ["notes"]
        }
    },
    {
        "name": "get_visual_history",
        "description": "Önceki görsel gözlemleri getir. Kullanıcının görünümündeki değişiklikleri karşılaştırmak için kullan.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    # Screen Sharing Tools
    {
        "name": "share_screen",
        "description": "Kullanıcının ekranını görmeye başla. Kamera duracak, ekran paylaşımı başlayacak.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "stop_screen_share",
        "description": "Ekran paylaşımını durdur ve kameraya geri dön.",
        "parameters": {"type": "OBJECT", "properties": {}}
    }
]

# Tool execution map
def execute_tool(name: str, args: dict) -> str:
    """Execute an AtomBase tool and return the result."""
    try:
        if name == "get_current_time":
            return get_current_time.invoke({})
        elif name == "list_files":
            return list_files.invoke({"directory": args.get("directory", ".")})
        elif name == "read_file":
            return read_file.invoke({"filename": args["filename"]})
        elif name == "write_file":
            return write_file.invoke({"filename": args["filename"], "content": args["content"]})
        elif name == "scan_workspace":
            return scan_workspace.invoke({"max_depth": args.get("max_depth", 2)})
        elif name == "run_terminal_command":
            return run_terminal_command.invoke({"command": args["command"]})
        elif name == "run_neofetch":
            return run_neofetch.invoke({})
        elif name == "delegate_coding":
            if CODING_AVAILABLE:
                result = delegate_coding(args["prompt"], args.get("context", ""))
                if result["success"]:
                    # Save the code to main Atomik workspace (not AtomBase)
                    workspace = os.path.join(os.path.dirname(__file__), "atom_workspace")
                    os.makedirs(workspace, exist_ok=True)
                    filepath = save_generated_code(result["filename"], result["code"], workspace)
                    return f"✅ Kod oluşturuldu: {result['filename']}\n\n{result['explanation']}\n\nDosya: {filepath}"
                else:
                    return f"❌ Kod oluşturulamadı: {result.get('error', 'Bilinmeyen hata')}"
            else:
                return "Coding module not available"
        # Memory tools
        elif name == "save_context":
            if MEMORY_AVAILABLE:
                return save_context(args["key"], args["value"])
            return "Memory module not available"
        elif name == "get_context_info":
            if MEMORY_AVAILABLE:
                return get_context_info(args["key"])
            return "Memory module not available"
        elif name == "get_memory_stats":
            if MEMORY_AVAILABLE:
                return get_memory_stats()
            return "Memory module not available"
        elif name == "clear_memory":
            if MEMORY_AVAILABLE:
                return clear_memory()
            return "Memory module not available"
        # Weather tool
        elif name == "get_weather":
            if WEATHER_AVAILABLE:
                return get_weather(args["city"])
            return "Weather module not available"
        # Camera tool - use latest frame from background capture
        elif name == "capture_frame":
            global _pending_camera_frame, _latest_image_payload
            if CAMERA_ENABLED and _latest_image_payload:
                # Use frame from background capture task (already open)
                _pending_camera_frame = _latest_image_payload
                return "📷 Görüntüyü analiz ediyorum..."
            elif CAMERA_AVAILABLE:
                # Fallback: try to capture manually
                result = capture_frame()
                if result["success"]:
                    import base64
                    _pending_camera_frame = {
                        "data": base64.b64decode(result["data"]),
                        "mime_type": result["mime_type"]
                    }
                    return "📷 Görüntüyü analiz ediyorum..."
                else:
                    return f"❌ Kamera hatası: {result['error']}"
            return "Kamera kullanılamıyor"
        # Exit tool - let Atomik respond then exit
        elif name == "exit_app":
            global _exit_requested
            _exit_requested = True
            # Return message for Atomik to speak, then exit after response
            return "Güle güle! Seninle sohbet etmek güzeldi. Tekrar görüşmek üzere!"
        # Visual Memory Tools
        elif name == "save_visual_observation":
            if VISUAL_MEMORY_AVAILABLE:
                return save_visual_observation(args["notes"])
            return "Görsel hafıza kullanılamıyor"
        elif name == "get_visual_history":
            if VISUAL_MEMORY_AVAILABLE:
                return get_visual_history()
            return "Görsel hafıza kullanılamıyor"
        # Screen Sharing Tools
        elif name == "share_screen":
            global VIDEO_MODE
            VIDEO_MODE = "screen"
            return "🖥️ Tamam! Kamerayı kapatıp ekranını izlemeye başlıyorum. 'Ekranı bırakabilirsin' dediğinde geri kameraya döneceğim."
        elif name == "stop_screen_share":
            VIDEO_MODE = "camera"
            return "📷 Ekran paylaşımı durduruldu. Kameraya geri dönüyorum!"
        else:
            return f"Unknown tool: {name}"
    except Exception as e:
        return f"Tool error: {str(e)}"

# Global state
_pending_camera_frame = None
_exit_requested = False

# Video Mode (camera or screen)
VIDEO_MODE = "camera"  # "camera" or "screen"

# VAD-based Camera Settings (improved for better visual intelligence)
CAMERA_ENABLED = CAMERA_AVAILABLE  # Use camera if available
FRAME_INTERVAL = 1.0  # Seconds between frame captures (faster = better visual context)
VAD_THRESHOLD = 600  # RMS threshold for speech detection (lower = more sensitive)
SPEECH_FRAME_INTERVAL = 3  # Send frame every N seconds during speech (continuous updates)
_latest_image_payload = None  # Stores latest camera frame
_is_speaking = False  # VAD state
_last_frame_time = 0  # Track when last frame was sent
VISUAL_MEMORY_AVAILABLE = True  # Set after imports

# ============================================================
# Audio Loop with Tool Calling
# ============================================================

pya = pyaudio.PyAudio()

client = genai.Client(http_options={"api_version": "v1beta"}, api_key=API_KEY)

# Config with tools
tools_config = [
    {"google_search": {}},  # Enable Google Search
    {"function_declarations": TOOL_DECLARATIONS}
]

config = types.LiveConnectConfig(
    response_modalities=["AUDIO"],
    output_audio_transcription={}, 
    input_audio_transcription={},
    system_instruction=SYSTEM_PROMPT,
    tools=tools_config,
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name="Aoede"
            )
        )
    )
)

class AudioLoop:
    def __init__(self):
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self._last_input_transcription = ""
        self._last_output_transcription = ""
        
    def clear_audio_queue(self):
        try:
            count = 0
            while not self.audio_in_queue.empty():
                self.audio_in_queue.get_nowait()
                count += 1
            if count > 0:
                print(f"{Colors.DIM}[Kesildi]{Colors.RESET}")
        except Exception:
            pass
    
    async def capture_frames(self):
        """Background task to continuously capture camera/screen frames"""
        global _latest_image_payload, CAMERA_ENABLED, VIDEO_MODE
        
        print(f"{Colors.GREEN}📷 Görüntü yakalama başlatılıyor...{Colors.RESET}")
        
        try:
            import cv2
            import io
            from PIL import Image
            
            cap = None
            sct = None
            
            while True:
                try:
                    if VIDEO_MODE == "camera":
                        # Camera mode
                        if cap is None or not cap.isOpened():
                            cap = await asyncio.to_thread(cv2.VideoCapture, 0)
                            if cap.isOpened():
                                print(f"{Colors.GREEN}📷 Kamera hazır (her {FRAME_INTERVAL}s frame){Colors.RESET}")
                            else:
                                await asyncio.sleep(FRAME_INTERVAL)
                                continue
                        
                        ret, frame = await asyncio.to_thread(cap.read)
                        if not ret:
                            await asyncio.sleep(FRAME_INTERVAL)
                            continue
                        
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        img = Image.fromarray(frame_rgb)
                        
                    elif VIDEO_MODE == "screen":
                        # Screen mode using mss (run all mss in thread to avoid thread-local issues)
                        try:
                            def grab_screen():
                                import mss
                                with mss.mss() as sct:
                                    monitor = sct.monitors[1]
                                    screenshot = sct.grab(monitor)
                                    return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                            
                            if not hasattr(self, '_screen_announced') or not self._screen_announced:
                                print(f"{Colors.GREEN}🖥️ Ekran paylaşımı başladı{Colors.RESET}")
                                self._screen_announced = True
                            
                            img = await asyncio.to_thread(grab_screen)
                            
                            # Release camera if switching to screen
                            if cap is not None:
                                cap.release()
                                cap = None
                                
                        except ImportError:
                            print(f"{Colors.YELLOW}🖥️ mss yüklü değil, pip install mss{Colors.RESET}")
                            VIDEO_MODE = "camera"
                            await asyncio.sleep(FRAME_INTERVAL)
                            continue
                    else:
                        await asyncio.sleep(FRAME_INTERVAL)
                        continue
                    
                    # Convert to JPEG
                    img.thumbnail([1536, 1536])
                    buffer = io.BytesIO()
                    img.save(buffer, format="JPEG", quality=90)
                    buffer.seek(0)
                    
                    _latest_image_payload = {
                        "mime_type": "image/jpeg",
                        "data": buffer.getvalue()
                    }
                    
                    await asyncio.sleep(FRAME_INTERVAL)
                    
                except Exception as e:
                    print(f"{Colors.DIM}📷 Frame hatası: {e}{Colors.RESET}")
                    await asyncio.sleep(FRAME_INTERVAL)
            
            if cap:
                cap.release()
                
        except ImportError:
            print(f"{Colors.YELLOW}📷 opencv-python yüklü değil{Colors.RESET}")
            CAMERA_ENABLED = False
        except Exception as e:
            print(f"{Colors.YELLOW}📷 Görüntü hatası: {e}{Colors.RESET}")
            CAMERA_ENABLED = False
    
    async def send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send(input=msg, end_of_turn=False)
    
    async def listen_audio(self):
        input_device_index = None
        for i in range(pya.get_device_count()):
            try:
                info = pya.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    stream = pya.open(
                        format=FORMAT, channels=CHANNELS,
                        rate=SEND_SAMPLE_RATE, input=True,
                        input_device_index=i, frames_per_buffer=CHUNK_SIZE
                    )
                    stream.close()
                    input_device_index = i
                    if "pulse" in info['name'].lower():
                        break
            except Exception:
                continue
        
        if input_device_index is None:
            print(f"{Colors.YELLOW}Mikrofon bulunamadı!{Colors.RESET}")
            return
            
        print(f"{Colors.GREEN}🎤 Mikrofon hazır{Colors.RESET}")
        
        audio_stream = pya.open(
            format=FORMAT, channels=CHANNELS,
            rate=SEND_SAMPLE_RATE, input=True,
            input_device_index=input_device_index,
            frames_per_buffer=CHUNK_SIZE,
        )
        
        while True:
            try:
                data = await asyncio.to_thread(
                    audio_stream.read, CHUNK_SIZE, 
                    exception_on_overflow=False
                )
                if self.out_queue:
                    await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
                # VAD Logic for Camera (ada_v2 style - send ONE frame at speech start)
                global _is_speaking, _latest_image_payload, _last_frame_time
                SILENCE_DURATION = 0.5  # Seconds of silence to confirm "done speaking"
                
                if CAMERA_ENABLED and _latest_image_payload:
                    # Calculate RMS
                    import struct
                    import math
                    count = len(data) // 2
                    if count > 0:
                        shorts = struct.unpack(f"<{count}h", data)
                        sum_squares = sum(s**2 for s in shorts)
                        rms = int(math.sqrt(sum_squares / count))
                    else:
                        rms = 0
                    
                    if rms > VAD_THRESHOLD:
                        # Speech detected - reset silence timer
                        if not hasattr(self, '_silence_start_time'):
                            self._silence_start_time = None
                        self._silence_start_time = None
                        
                        import time
                        should_send_frame = False
                        
                        if not _is_speaking:
                            # NEW speech utterance started
                            _is_speaking = True
                            should_send_frame = True
                            _last_frame_time = time.time()
                        elif time.time() - _last_frame_time >= 2.0:
                            # Periodic refresh every 5 seconds during speech
                            should_send_frame = True
                            _last_frame_time = time.time()
                        
                        if should_send_frame and self.out_queue:
                            await self.out_queue.put(_latest_image_payload)
                            #print(f"{Colors.DIM}📷 Frame güncellendi{Colors.RESET}")
                    else:
                        # Silence
                        import time
                        if _is_speaking:
                            if not hasattr(self, '_silence_start_time') or self._silence_start_time is None:
                                self._silence_start_time = time.time()
                            elif time.time() - self._silence_start_time > SILENCE_DURATION:
                                # Silence confirmed, reset state
                                _is_speaking = False
                                self._silence_start_time = None
                            
            except Exception as e:
                await asyncio.sleep(0.1)
    
    async def receive_audio(self):
        user_buffer = ""
        agent_buffer = ""
        
        try:
            while True:
                turn = self.session.receive()
                async for response in turn:
                    # Handle Audio Data
                    if data := response.data:
                        self.audio_in_queue.put_nowait(data)
                    
                    # Handle Tool Calls
                    if response.tool_call:
                        print(f"\n{Colors.BLUE}🔧 Araç çağrısı algılandı{Colors.RESET}")
                        function_responses = []
                        
                        for fc in response.tool_call.function_calls:
                            print(f"{Colors.BLUE}   → {fc.name}({fc.args}){Colors.RESET}")
                            
                            # Execute the tool
                            if ATOMBASE_AVAILABLE:
                                result = execute_tool(fc.name, fc.args or {})
                            else:
                                result = "AtomBase araçları yüklenmedi"
                            
                            # Truncate long results for voice
                            if len(result) > 500:
                                result = result[:500] + "... (kırpıldı)"
                            
                            print(f"{Colors.BLUE}   ✓ Sonuç: {result[:100]}...{Colors.RESET}")
                            
                            # For NON_BLOCKING tools, add scheduling to control announcement
                            response_data = {"result": result}
                            if fc.name == "delegate_coding":
                                # WHEN_IDLE: Wait for model to finish speaking, then announce
                                response_data["scheduling"] = "WHEN_IDLE"
                            
                            function_response = types.FunctionResponse(
                                id=fc.id,
                                name=fc.name,
                                response=response_data
                            )
                            function_responses.append(function_response)
                        
                        # Send tool responses back
                        await self.session.send_tool_response(function_responses=function_responses)
                        
                        # Send camera frame AFTER tool response (if captured)
                        global _pending_camera_frame
                        if _pending_camera_frame and self.out_queue:
                            await self.out_queue.put(_pending_camera_frame)
                            _pending_camera_frame = None
                            print(f"{Colors.BLUE}   📷 Görüntü Gemini'ye gönderildi{Colors.RESET}")
                    
                    # Handle Transcription
                    if response.server_content:
                        if response.server_content.input_transcription:
                            transcript = response.server_content.input_transcription.text
                            if transcript and transcript != self._last_input_transcription:
                                delta = transcript
                                if transcript.startswith(self._last_input_transcription):
                                    delta = transcript[len(self._last_input_transcription):]
                                self._last_input_transcription = transcript
                                
                                if delta:
                                    self.clear_audio_queue()
                                    if agent_buffer:
                                        print()
                                        agent_buffer = ""
                                    user_buffer += delta
                                    # Clear line and print once
                                    print(f"\033[2K\r{Colors.GREEN}[Sen]{Colors.RESET} {user_buffer}", end="", flush=True)
                        
                        if response.server_content.output_transcription:
                            transcript = response.server_content.output_transcription.text
                            if transcript and transcript != self._last_output_transcription:
                                # Calculate delta (ada_v2 style)
                                delta = transcript
                                if transcript.startswith(self._last_output_transcription):
                                    delta = transcript[len(self._last_output_transcription):]
                                self._last_output_transcription = transcript
                                
                                if delta:
                                    if user_buffer:
                                        print()
                                        user_buffer = ""
                                    # Print delta inline (no line clearing)
                                    if not agent_buffer:
                                        print(f"{Colors.MAGENTA}[Atomik]{Colors.RESET} ", end="", flush=True)
                                    print(delta, end="", flush=True)
                                    agent_buffer += delta
                        
                        if response.server_content.turn_complete:
                            # Save messages to history
                            if MEMORY_AVAILABLE:
                                if hasattr(self, '_complete_user_msg') and self._complete_user_msg:
                                    add_to_history("user", self._complete_user_msg)
                                if hasattr(self, '_complete_agent_msg') and self._complete_agent_msg:
                                    add_to_history("agent", self._complete_agent_msg)
                            
                            if agent_buffer:
                                self._complete_agent_msg = agent_buffer
                                print()
                                agent_buffer = ""
                            if user_buffer:
                                self._complete_user_msg = user_buffer
                                print()
                                user_buffer = ""
                            self._last_input_transcription = ""
                            self._last_output_transcription = ""
                            
                            # Check for exit request after Atomik responded
                            global _exit_requested
                            if _exit_requested:
                                print(f"\n{Colors.CYAN}👋 Görüşmek üzere!{Colors.RESET}")
                                await asyncio.sleep(1)  # Let audio finish
                                raise asyncio.CancelledError("User requested exit")
                            
        except Exception as e:
            print(f"\n{Colors.YELLOW}Bağlantı kapandı: {e}{Colors.RESET}")
            raise
    
    async def play_audio(self):
        output_device_index = None
        for i in range(pya.get_device_count()):
            try:
                info = pya.get_device_info_by_index(i)
                if info['maxOutputChannels'] > 0:
                    stream = pya.open(
                        format=FORMAT, channels=CHANNELS,
                        rate=RECEIVE_SAMPLE_RATE, output=True,
                        output_device_index=i
                    )
                    stream.close()
                    output_device_index = i
                    if "pulse" in info['name'].lower():
                        break
            except Exception:
                continue
        
        if output_device_index is None:
            print(f"{Colors.YELLOW}Hoparlör bulunamadı!{Colors.RESET}")
            return
            
        print(f"{Colors.GREEN}🔊 Hoparlör hazır{Colors.RESET}")
        
        stream = pya.open(
            format=FORMAT, channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE, output=True,
            output_device_index=output_device_index,
        )
        
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)
    
    async def run(self):
        print_header()
        
        if ATOMBASE_AVAILABLE:
            print(f"{Colors.CYAN}Yüklü araçlar: get_current_time, list_files, read_file, write_file, scan_workspace, run_terminal_command, run_neofetch{Colors.RESET}")
        
        print(f"{Colors.YELLOW}Gemini Live API'ye bağlanılıyor...{Colors.RESET}")
        
        try:
            async with (
                client.aio.live.connect(model=MODEL, config=config) as session,
                asyncio.TaskGroup() as tg,
            ):
                self.session = session
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=10)
                
                print(f"{Colors.GREEN}✓ Bağlandı!{Colors.RESET}")
                print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")
                print(f"{Colors.CYAN}Konuşmaya başlayabilirsiniz...{Colors.RESET}\n")
                
                tg.create_task(self.send_realtime())
                tg.create_task(self.listen_audio())
                tg.create_task(self.receive_audio())
                tg.create_task(self.play_audio())
                
                # Start camera capture task (ada_v2 style)
                if CAMERA_ENABLED:
                    tg.create_task(self.capture_frames())
                
                while True:
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            print(f"\n{Colors.YELLOW}Çıkılıyor...{Colors.RESET}")
        except Exception as e:
            print(f"\n{Colors.YELLOW}Hata: {e}{Colors.RESET}")
            traceback.print_exc()

async def main():
    audio_loop = AudioLoop()
    await audio_loop.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.CYAN}Hoşça kal!{Colors.RESET}")
    finally:
        pya.terminate()
