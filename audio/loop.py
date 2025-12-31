"""
Audio Loop - Main audio processing class
"""
import warnings
# Suppress ALL deprecation and runtime warnings BEFORE any imports
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

import asyncio
import os
import sys
import shutil  # Terminal boyutu için
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
from .echo_cancel import aec
from core.connection import get_connection_manager
from audio.local_loop import LocalAudioLoop

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

# Import RAG memory for automatic conversation saving
try:
    from tools.memory.rag_memory import remember_conversation
    RAG_AVAILABLE = True
except ImportError:
    remember_conversation = lambda *args, **kwargs: None
    RAG_AVAILABLE = False

# Import SQLite session database for persistent history
try:
    from tools.memory.session_db import save_message as db_save_message, start_session as db_start_session
    SESSION_DB_AVAILABLE = True
except ImportError:
    db_save_message = lambda *args: None
    db_start_session = lambda: None
    SESSION_DB_AVAILABLE = False

# Import learning module for startup context and fact extraction
try:
    from tools.memory.learning import get_startup_context, process_conversation_for_learning, log_mood
    LEARNING_AVAILABLE = True
except ImportError:
    get_startup_context = lambda: ""
    process_conversation_for_learning = lambda *args: None
    log_mood = lambda *args: None
    LEARNING_AVAILABLE = False


class AudioLoop:
    def __init__(self):
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self._last_input_transcription = ""
        self._last_output_transcription = ""
        self._silence_start_time = None
        self._skip_next_transcription = False  # Skip stale transcription after tool call
        self._vad_chunk_counter = 0  # Performance: VAD every 3 chunks
        
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
                    # Echo Cancellation: Process microphone data
                    clean_data = aec.process_microphone(data)
                    await self.out_queue.put({"data": clean_data, "mime_type": "audio/pcm"})
                
                # VAD Logic for Camera (Performance: check every 3 chunks)
                self._vad_chunk_counter += 1
                if CAMERA_ENABLED and state.latest_image_payload and self._vad_chunk_counter >= 3:
                    self._vad_chunk_counter = 0  # Reset counter
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
                        # Wait for audio to finish playing before executing tools
                        # This prevents tools from interrupting mid-sentence
                        while not self.audio_in_queue.empty():
                            await asyncio.sleep(0.1)
                        
                        # Print transition phrase before tool call
                        if agent_buffer:
                            print()  # New line after previous agent text
                            agent_buffer = ""
                        
                        print(f"\n{Colors.BLUE}🔧 Araç çağrısı algılandı{Colors.RESET}")
                        function_responses = []
                        
                        for fc in response.tool_call.function_calls:
                            print(f"{Colors.BLUE}   → {fc.name}({fc.args}){Colors.RESET}")
                            
                            if ATOMBASE_AVAILABLE:
                                result = execute_tool(fc.name, fc.args or {})
                            else:
                                result = "AtomBase araçları yüklenmedi"
                            
                            if len(result) > 8000:
                                result = result[:8000] + "... (kırpıldı)"
                            
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
                        
                        # Reset transcription state and skip next stale message after tool call
                        # This prevents "Bitince haber veririm" type messages from appearing AFTER tool result
                        self._last_output_transcription = ""
                        self._skip_next_transcription = True  # Skip the stale transcription
                        
                        # Clear any stale audio that was queued before tool execution
                        self.clear_audio_queue()
                        
                        # Small delay to let any pending transcription messages pass through
                        await asyncio.sleep(0.2)
                        
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
                                    # Terminal genişliğine göre kısalt (wrap bug'ı önlemek için)
                                    try:
                                        term_width = shutil.get_terminal_size().columns
                                    except:
                                        term_width = 80
                                    prefix = f"{Colors.GREEN}[Sen]{Colors.RESET} "
                                    prefix_len = 6  # "[Sen] " görünen uzunluk
                                    max_text_len = term_width - prefix_len - 1
                                    display_text = user_buffer[-max_text_len:] if len(user_buffer) > max_text_len else user_buffer
                                    print(f"\033[2K\r{prefix}{display_text}", end="", flush=True)
                        
                        if response.server_content.output_transcription:
                            transcript = response.server_content.output_transcription.text
                            if transcript and transcript != self._last_output_transcription:
                                # Skip stale transcription that came with tool call
                                if self._skip_next_transcription:
                                    self._skip_next_transcription = False
                                    self._last_output_transcription = transcript
                                    continue  # Skip this stale message
                                
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
                            
                            # Auto-save to RAG memory (persistent across sessions)
                            if RAG_AVAILABLE and hasattr(self, '_complete_user_msg') and hasattr(self, '_complete_agent_msg'):
                                if self._complete_user_msg and self._complete_agent_msg:
                                    summary = f"Sen: {self._complete_user_msg[:150]} → Atomik: {self._complete_agent_msg[:150]}"
                                    remember_conversation(summary, {"type": "auto"})
                            
                            # Auto-save to SQLite database (searchable history)
                            if SESSION_DB_AVAILABLE:
                                if hasattr(self, '_complete_user_msg') and self._complete_user_msg:
                                    db_save_message("user", self._complete_user_msg)
                                if hasattr(self, '_complete_agent_msg') and self._complete_agent_msg:
                                    db_save_message("agent", self._complete_agent_msg)
                            
                            # Extract facts for learning (preferences, projects, etc.)
                            if LEARNING_AVAILABLE:
                                if hasattr(self, '_complete_user_msg') and hasattr(self, '_complete_agent_msg'):
                                    if self._complete_user_msg and self._complete_agent_msg:
                                        process_conversation_for_learning(self._complete_user_msg, self._complete_agent_msg)
                            
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
            # Echo Cancellation: Register speaker output
            aec.feed_speaker(bytestream)
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
                
                # ONLY observe when there's no active conversation
                # Check if agent or user is currently speaking/listening
                is_conversation_active = (
                    state.is_speaking or  # User is talking
                    not self.audio_in_queue.empty()  # Agent is playing audio
                )
                
                if observation_counter >= 6 and state.latest_image_payload and not is_conversation_active:
                    observation_counter = 0
                    
                    try:
                        from core.vision_analyzer import analyze_change
                        
                        # Call Vision AI to compare frames - returns dict
                        result = await analyze_change(state.latest_image_payload)
                        
                        # Handle both dict and list responses
                        if isinstance(result, list):
                            result = result[0] if result else {"type": "NONE"}
                        
                        result_type = result.get("type", "NONE")
                        description = result.get("description", "")
                        
                        if result_type == "INTERACTION":
                            # Only interrupt if REALLY important (don't spam)
                            # For now, skip interrupting - let user initiate
                            pass  # Disabled: was causing conversation interruption
                                
                        elif result_type == "MEMORY":
                            # Silently log to context (no print, no interrupt)
                            # This is background observation only
                            pass  # Disabled: was causing conversation interruption
                                
                    except Exception as e:
                        error_msg = str(e)
                        # Silent handling for specific errors to avoid console spam
                        if "429" in error_msg:
                            await asyncio.sleep(10)
                        elif "404" in error_msg:
                            await asyncio.sleep(30)
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
        # 1. Check Connection Strategy
        cm = get_connection_manager()
        
        # Initial Check
        if not cm.is_online:
            print(f"{Colors.RED}⚠️ İnternet Yok! Offline Mod Başlatılıyor...{Colors.RESET}")
            local_loop = LocalAudioLoop()
            await local_loop.run()
            return

        # If online, proceed with Gemini
        print_header()
        
        if ATOMBASE_AVAILABLE:
            print(f"{Colors.CYAN}Yüklü araçlar: get_current_time, get_current_location, list_files, read_file, write_file, scan_workspace, run_terminal_command, run_neofetch{Colors.RESET}")
            
            # Cache location at startup
            try:
                from AtomBase.tools.location import get_current_location
                import json
                print(f"{Colors.YELLOW}📍 Konum tespit ediliyor...{Colors.RESET}", end=" ", flush=True)
                location_data = get_current_location.invoke({})
                state.cached_location = location_data
                city = location_data.get("city", "Bilinmiyor")
                country = location_data.get("country", "")
                print(f"{Colors.GREEN}{city}, {country}{Colors.RESET}")
            except Exception as e:
                print(f"{Colors.YELLOW}Konum alınamadı{Colors.RESET}")
        
        print(f"{Colors.YELLOW}Gemini Live API'ye bağlanılıyor...{Colors.RESET}")
        
        self.model_to_use = MODEL
        
        while True:
            try:
                print(f"{Colors.DIM}Model: {self.model_to_use}{Colors.RESET}")
                async with (
                    client.aio.live.connect(model=self.model_to_use, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session = session
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue = asyncio.Queue(maxsize=10)
                    
                    print(f"{Colors.GREEN}✓ Bağlandı! ({self.model_to_use}){Colors.RESET}")
                    
                    # Load and inject startup context (memories, profile, mood)
                    if LEARNING_AVAILABLE:
                        startup_ctx = get_startup_context()
                        if startup_ctx:
                            print(f"{Colors.CYAN}🧠 Hafıza yükleniyor...{Colors.RESET}")
                            # Send context as initial text to Gemini
                            await session.send_client_content(
                                turns=[{"role": "user", "parts": [{"text": f"[SİSTEM HAFIZA YÜKLEMESI - KULLANICIYA GÖRÜNMEZ]\n{startup_ctx}"}]}],
                                turn_complete=True
                            )
                            # Wait for context to be processed before accepting user input
                            await asyncio.sleep(1)
                    
                    print(f"{Colors.DIM}{'─' * 50}{Colors.RESET}")
                    print(f"{Colors.CYAN}Konuşmaya başlayabilirsiniz...{Colors.RESET}\n")
                    
                    tg.create_task(self.send_realtime())
                    tg.create_task(self.listen_audio())
                    tg.create_task(self.receive_audio())
                    tg.create_task(self.play_audio())
                    tg.create_task(self.proactive_check())
                    
                    if CAMERA_ENABLED:
                        tg.create_task(capture_frames())
                    
                    session_start_time = time.time()
                    
                    while True:
                        await asyncio.sleep(1)
                        
                        # Proaktif Oturum Yenileme (9 dakika kuralı)
                        limit_seconds = 540  # 9 dakika
                        if time.time() - session_start_time > limit_seconds:
                            print(f"{Colors.YELLOW}⏳ Oturum süresi doldu ({limit_seconds}sn), proaktif yenileniyor...{Colors.RESET}")
                            
                            # Kullanıcıya doğal bir bildirim (sesli)
                            try:
                                msg = "Şey, ufak bir teknik aksaklık yaşıyorum, bağlantıyı tazeleyip hemen geliyorum. Bir saniye..."
                                await self.session.send(input=msg, end_of_turn=True)
                                await asyncio.sleep(6)  # Mesajın iletilmesi ve seslendirilmesi için bekle
                            except:
                                pass
                                
                            raise Exception("Session timeout refresh (Auto-Reconnect)")
                        
            except asyncio.CancelledError:
                print(f"\n{Colors.YELLOW}Çıkılıyor...{Colors.RESET}")
                return  # Don't reconnect on intentional exit
            except Exception as e:
                print(f"\n{Colors.YELLOW}Bağlantı koptu: {e}{Colors.RESET}")
                
                # Check if this is a session timeout/policy error (reconnectable)
                # Handle Python 3.11+ ExceptionGroups from TaskGroup
                should_reconnect = False
                error_is_policy_violation = False
                
                errors_to_check = [e]
                if hasattr(e, 'exceptions'):
                    errors_to_check.extend(e.exceptions)
                    
                for err in errors_to_check:
                    err_str = str(err).lower()
                    if "1008" in err_str or "policy" in err_str or "entity" in err_str or "404" in err_str:
                         error_is_policy_violation = True
                         should_reconnect = True
                         break
                    if any(x in err_str for x in ['timeout', 'closed', 'auto-reconnect']):
                        should_reconnect = True
                        break
                
                if should_reconnect:
                    if error_is_policy_violation:
                         # Try fallback logic
                         print(f"{Colors.RED}⚠️ Model hatası/Politika ihlali algılandı: {self.model_to_use}{Colors.RESET}")
                         
                         # Import here to avoid circular dependency in top-level
                         from core.config import FALLBACK_MODELS
                         # We need access to the ORIGINAL MODEL constant from config, 
                         # but we shadowed it with the import in the loop.
                         # Let's import the specific module to get the constant cleanly
                         import core.config
                         default_model = core.config.MODEL
                         
                         current_model = self.model_to_use
                         
                         # Check if we can switch to a fallback
                         next_model = None
                         
                         # Case 1: We are currently on the default model
                         if current_model == default_model:
                             if len(FALLBACK_MODELS) > 0:
                                 next_model = FALLBACK_MODELS[0]
                                 
                         # Case 2: We are already on a fallback model
                         elif current_model in FALLBACK_MODELS:
                             idx = FALLBACK_MODELS.index(current_model)
                             if idx + 1 < len(FALLBACK_MODELS):
                                 next_model = FALLBACK_MODELS[idx + 1]
                                 
                         if next_model:
                             print(f"{Colors.YELLOW}🔄 Fallback modeline geçiliyor: {next_model}{Colors.RESET}")
                             self.model_to_use = next_model
                         else:
                             print(f"{Colors.RED}❌ Tüm fallback modelleri denendi, mevcut model çalışmıyor: {self.model_to_use}{Colors.RESET}")
                             # Reset to default for next retry loop after a long pause, or just keep trying the last one?
                             # Let's try the default one again after a long pause, maybe it was temporary.
                             self.model_to_use = default_model
                             print(f"{Colors.DIM}10 saniye sonra varsayılan model ile tekrar denenecek...{Colors.RESET}")
                             await asyncio.sleep(10)
                             
                    print(f"{Colors.CYAN}🔄 Otomatik yeniden bağlanılıyor...{Colors.RESET}")
                    await asyncio.sleep(2)  # Brief pause before reconnect
                    
                    # Reset state for new session
                    self._last_input_transcription = ""
                    self._last_output_transcription = ""
                    continue # Re-start the while loop to connect again
                else:
                    # Non-recoverable error? Let's try to reconnect anyway for robustness
                    print(f"{Colors.RED}Beklenmedik hata, yine de 5sn sonra tekrar denenecek...{Colors.RESET}")
                    await asyncio.sleep(5)
                    continue



def cleanup():
    pya.terminate()
