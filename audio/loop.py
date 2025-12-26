"""
Audio Loop - Main audio processing class
"""
import asyncio
import os
import sys
import pyaudio
import struct
import math
import time

# Ensure project root is in path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from google import genai
from google.genai import types

from core import (
    API_KEY, FORMAT, CHANNELS, SEND_SAMPLE_RATE, RECEIVE_SAMPLE_RATE,
    CHUNK_SIZE, MODEL, VAD_THRESHOLD, SILENCE_DURATION, SYSTEM_PROMPT
)
from core.colors import Colors, print_header
from core import state
from tools import TOOL_DECLARATIONS, execute_tool, ATOMBASE_AVAILABLE, CAMERA_ENABLED, MEMORY_AVAILABLE
from .video import capture_frames

# PyAudio instance
pya = pyaudio.PyAudio()

# Gemini client
client = genai.Client(http_options={"api_version": "v1beta"}, api_key=API_KEY)

# Config with tools
tools_config = [
    {"google_search": {}},
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
                # Sesler: Aoede(kadın), Charon(erkek,derin), Fenrir(erkek), Kore(kadın), Puck(erkek,genç)
                voice_name="Kore"
            )
        )
    )
)

# Import memory function if available
try:
    from AtomBase.tools.memory import add_to_history
except ImportError:
    add_to_history = lambda *args: None


class AudioLoop:
    def __init__(self):
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self._last_input_transcription = ""
        self._last_output_transcription = ""
        self._silence_start_time = None
        
        # Set global reference needed by tools
        state.active_loop = self
        
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
                
                # VAD Logic for Camera
                if CAMERA_ENABLED and state.latest_image_payload:
                    count = len(data) // 2
                    if count > 0:
                        shorts = struct.unpack(f"<{count}h", data)
                        sum_squares = sum(s**2 for s in shorts)
                        rms = int(math.sqrt(sum_squares / count))
                    else:
                        rms = 0
                    
                    if rms > VAD_THRESHOLD:
                        self._silence_start_time = None
                        
                        should_send_frame = False
                        
                        if not state.is_speaking:
                            state.is_speaking = True
                            should_send_frame = True
                            state.last_frame_time = time.time()
                        elif time.time() - state.last_frame_time >= 1.0:
                            # Send frame every 1 second during speech for responsive updates
                            should_send_frame = True
                            state.last_frame_time = time.time()
                        
                        if should_send_frame and self.out_queue:
                            await self.out_queue.put(state.latest_image_payload)
                    else:
                        if state.is_speaking:
                            if self._silence_start_time is None:
                                self._silence_start_time = time.time()
                            elif time.time() - self._silence_start_time > SILENCE_DURATION:
                                state.is_speaking = False
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
                    if data := response.data:
                        self.audio_in_queue.put_nowait(data)
                    
                    if response.tool_call:
                        print(f"\n{Colors.BLUE}🔧 Araç çağrısı algılandı{Colors.RESET}")
                        function_responses = []
                        
                        for fc in response.tool_call.function_calls:
                            print(f"{Colors.BLUE}   → {fc.name}({fc.args}){Colors.RESET}")
                            
                            if ATOMBASE_AVAILABLE:
                                result = execute_tool(fc.name, fc.args or {})
                            else:
                                result = "AtomBase araçları yüklenmedi"
                            
                            if len(result) > 500:
                                result = result[:500] + "... (kırpıldı)"
                            
                            print(f"{Colors.BLUE}   ✓ Sonuç: {result[:100]}...{Colors.RESET}")
                            
                            response_data = {"result": result}
                            if fc.name == "delegate_coding":
                                response_data["scheduling"] = "WHEN_IDLE"
                            
                            function_response = types.FunctionResponse(
                                id=fc.id,
                                name=fc.name,
                                response=response_data
                            )
                            function_responses.append(function_response)
                        
                        await self.session.send_tool_response(function_responses=function_responses)
                        
                        if state.pending_camera_frame and self.out_queue:
                            await self.out_queue.put(state.pending_camera_frame)
                            state.pending_camera_frame = None
                            print(f"{Colors.BLUE}   📷 Görüntü Gemini'ye gönderildi{Colors.RESET}")
                    
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
                                    print(f"\033[2K\r{Colors.GREEN}[Sen]{Colors.RESET} {user_buffer}", end="", flush=True)
                        
                        if response.server_content.output_transcription:
                            transcript = response.server_content.output_transcription.text
                            if transcript and transcript != self._last_output_transcription:
                                delta = transcript
                                if transcript.startswith(self._last_output_transcription):
                                    delta = transcript[len(self._last_output_transcription):]
                                self._last_output_transcription = transcript
                                
                                if delta:
                                    if user_buffer:
                                        print()
                                        user_buffer = ""
                                    if not agent_buffer:
                                        print(f"{Colors.MAGENTA}[Atomik]{Colors.RESET} ", end="", flush=True)
                                    
                                    # Filter INT_ACK for silent updates
                                    if "INT_ACK" in delta:
                                        delta = delta.replace("INT_ACK", "").strip()
                                        # Clear audio queue effectively silencing the turn
                                        self.clear_audio_queue()
                                    
                                    if delta:
                                        print(delta, end="", flush=True)
                                        agent_buffer += delta
                        
                        if response.server_content.turn_complete:
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
                            
                            if state.exit_requested:
                                print(f"\n{Colors.CYAN}👋 Görüşmek üzere!{Colors.RESET}")
                                await asyncio.sleep(1)
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
    
    async def proactive_check(self):
        """Background task for reminders, watchers, and continuous observation"""
        from core.proactive import check_proactive, get_watcher_conditions, trigger_watcher
        
        print(f"{Colors.GREEN}⏰ Proaktif sistem hazır{Colors.RESET}")
        
        last_frame_hash = None
        observation_counter = 0
        frame_history = []  # Son N frame'in hash'leri
        last_observation_time = 0
        
        while True:
            try:
                await asyncio.sleep(1)
                
                messages = []
                
                # 1. Check for due reminders
                reminder_messages = check_proactive()
                messages.extend(reminder_messages)
                
                # 2. Check explicit watchers
                watcher_conditions = get_watcher_conditions()
                if watcher_conditions and state.latest_image_payload:
                    current_hash = hash(state.latest_image_payload.get('data', b'')[:1000])
                    
                    if last_frame_hash is not None and current_hash != last_frame_hash:
                        for condition in watcher_conditions:
                            if any(word in condition.lower() for word in ['değiş', 'ekran', 'sayfa', 'change']):
                                result = trigger_watcher(condition)
                                if result:
                                    messages.append(result)
                                    print(f"{Colors.GREEN}👁️ Watcher tetiklendi: {condition}{Colors.RESET}")
                    
                    last_frame_hash = current_hash
                
                # 3. Vision Analyzer - AI-based frame comparison every 6 seconds
                observation_counter += 1
                
                if observation_counter >= 6 and state.latest_image_payload:
                    observation_counter = 0
                    
                    try:
                        from core.vision_analyzer import analyze_change
                        
                        # Call Vision AI to compare frames - returns dict
                        result = await analyze_change(state.latest_image_payload)
                        result_type = result.get("type", "NONE")
                        description = result.get("description", "")
                        
                        if result_type == "INTERACTION":
                            # Speak immediately!
                            if self.session and self.out_queue:
                                await self.out_queue.put(state.latest_image_payload)
                                change_prompt = f"[DEĞİŞİKLİK]: {description}"
                                await self.session.send(input=change_prompt, end_of_turn=True)
                                print(f"{Colors.GREEN}🗣️ Etkileşim: {description[:50]}...{Colors.RESET}")
                                
                        elif result_type == "MEMORY":
                            # Just log to context silently
                            if self.session:
                                # Send as INFO message with end_of_turn=False!
                                # This updates context but generates NO audio/response.
                                info_prompt = f"[BİLGİ]: {description}"
                                await self.session.send(input=info_prompt, end_of_turn=False)
                                print(f"{Colors.DIM}🧠 Hafıza: {description[:50]}...{Colors.RESET}")
                                
                    except Exception as e:
                        error_msg = str(e)
                        # Silent handling for specific errors to avoid console spam
                        if "429" in error_msg:
                            print(f"{Colors.YELLOW}⚠️ Vision Hız Sınırı (429) - Bekleniyor...{Colors.RESET}")
                            await asyncio.sleep(10) # Wait longer on rate limit
                        elif "404" in error_msg:
                            print(f"{Colors.RED}❌ Vision Model Bulunamadı (404) - Lütfen 'vision_analyzer.py' dosyasındaki modeli kontrol et.{Colors.RESET}")
                            await asyncio.sleep(30) # Wait very long to not spam log
                        elif "INT_ACK" not in error_msg: # Don't log expected silent ack
                            print(f"{Colors.DIM}Analyzer hatası: {e}{Colors.RESET}")
                        pass
                
                # Send proactive messages (reminders, watchers)
                for msg in messages:
                    if self.session:
                        print(f"{Colors.MAGENTA}⏰ Proaktif: {msg[:60]}...{Colors.RESET}")
                        
                        if state.latest_image_payload and self.out_queue:
                            await self.out_queue.put(state.latest_image_payload)
                        
                        await self.session.send(input=msg, end_of_turn=True)
                        await asyncio.sleep(2)  # Wait for response
                
            except Exception as e:
                print(f"{Colors.DIM}⏰ Hata: {e}{Colors.RESET}")
                await asyncio.sleep(1)
    
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
                tg.create_task(self.proactive_check())
                
                if CAMERA_ENABLED:
                    tg.create_task(capture_frames())
                
                while True:
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            print(f"\n{Colors.YELLOW}Çıkılıyor...{Colors.RESET}")
        except Exception as e:
            import traceback
            print(f"\n{Colors.YELLOW}Hata: {e}{Colors.RESET}")
            traceback.print_exc()


def cleanup():
    pya.terminate()
