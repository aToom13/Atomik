import os
import logging
import subprocess
import tempfile
import numpy as np
import threading
import queue
from typing import Optional

logger = logging.getLogger("atomik.audio.tts")

# Check for Bark TTS (best quality)
BARK_AVAILABLE = False
try:
    from transformers import AutoProcessor, AutoModel
    import torch
    import scipy.io.wavfile
    BARK_AVAILABLE = True
except ImportError:
    pass

# Fallback to Piper TTS
PIPER_AVAILABLE = False
try:
    from piper import PiperVoice
    import wave
    PIPER_AVAILABLE = True
except ImportError:
    pass

# Last fallback to pyttsx3
PYTTSX3_AVAILABLE = False
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    pass

class OfflineTTS:
    def __init__(self, reference_wav_path: str = None):
        self.bark_processor = None
        self.bark_model = None
        self.piper_voice = None
        self.pyttsx3_engine = None
        self.tts_type = None
        self.device = "cuda" if (BARK_AVAILABLE and torch.cuda.is_available()) else "cpu"
        
        # Audio Queue for non-blocking playback
        self.speech_queue = queue.Queue()
        self.is_speaking_flag = False
        
        # Start worker thread
        self.worker_thread = threading.Thread(target=self._speech_worker, daemon=True)
        self.worker_thread.start()
        
        # Use Piper first (fast, decent quality)
        if PIPER_AVAILABLE:
            try:
                # Use Turkish models (priority: fahrettin > dfki)
                base_path = os.path.join(os.path.dirname(__file__), "piper_models")
                models = ["tr_TR-fahrettin-medium.onnx", "tr_TR-dfki-medium.onnx"]
                model_path = None
                
                for m in models:
                    p = os.path.join(base_path, m)
                    if os.path.exists(p):
                        model_path = p
                        logger.info(f"Selected Piper model: {m}")
                        break
                
                if model_path:
                    logger.info("Loading Piper TTS...")
                    self.piper_voice = PiperVoice.load(model_path)
                    self.tts_type = "piper"
                    logger.info("Piper TTS Ready")
                else:
                    logger.warning(f"No Piper models found in {base_path}")
                    
            except Exception as e:
                logger.warning(f"Piper init failed: {e}")
        
        # Last fallback to pyttsx3
        if not self.tts_type and PYTTSX3_AVAILABLE:
            try:
                logger.info("Falling back to pyttsx3")
                self.pyttsx3_engine = pyttsx3.init()
                self.tts_type = "pyttsx3"
                logger.info("pyttsx3 TTS Ready")
            except Exception as e:
                logger.error(f"pyttsx3 init failed: {e}")

    @property
    def is_speaking(self):
        """Check if currently speaking or has queued speech"""
        return self.is_speaking_flag or not self.speech_queue.empty()

    def speak(self, text: str, async_play: bool = True):
        """Queue text for speech"""
        if not text or not text.strip():
            return
        # print(f"🔊 Atomik: {text}") # Zaten local_loop'ta basılıyor
        self.speech_queue.put(text)
        
    def _speech_worker(self):
        """Worker thread processing speech queue"""
        while True:
            text = self.speech_queue.get()
            self.is_speaking_flag = True
            try:
                if self.tts_type == "bark":
                    self._speak_bark(text)
                elif self.tts_type == "piper":
                    self._speak_piper(text)
                elif self.tts_type == "pyttsx3":
                    self._speak_pyttsx3(text)
            except Exception as e:
                logger.error(f"Speech worker error: {e}")
            finally:
                self.is_speaking_flag = False
                self.speech_queue.task_done()
    
    def _speak_bark(self, text: str):
        """Speak using Bark TTS"""
        try:
            # Add woman voice prompt for natural female voice
            voice_preset = "v2/en_speaker_9"  # Female voice
            
            inputs = self.bark_processor(
                text=[text],
                return_tensors="pt",
                voice_preset=voice_preset
            )
            
            # Generate speech
            speech_values = self.bark_model.generate(**inputs, do_sample=True)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            
            sampling_rate = self.bark_model.generation_config.sample_rate
            scipy.io.wavfile.write(
                temp_path, 
                rate=sampling_rate, 
                data=speech_values.cpu().numpy().squeeze()
            )
            
            # Play audio
            self._play_audio(temp_path)
            
            # Cleanup
            try:
                os.unlink(temp_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Bark speak error: {e}")
            # Fallback to pyttsx3
            if self.pyttsx3_engine:
                self._speak_pyttsx3(text)
    
    def _speak_piper(self, text: str):
        """Speak using Piper TTS"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name
            
            import wave
            with wave.open(temp_path, "wb") as wav_file:
                self.piper_voice.synthesize_wav(text, wav_file)
            
            self._play_audio(temp_path)
            
            try:
                os.unlink(temp_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Piper speak error: {e}")
    
    def _speak_pyttsx3(self, text: str):
        """Speak using pyttsx3"""
        try:
            self.pyttsx3_engine.say(text)
            self.pyttsx3_engine.runAndWait()
        except Exception as e:
            logger.error(f"pyttsx3 error: {e}")
    
    def _play_audio(self, filepath: str):
        """Play audio file using available player"""
        # Try playing with paplay first (PulseAudio)
        players = [
            ["paplay", filepath],
            ["pw-play", filepath],
            ["aplay", "-q", filepath],
            ["ffplay", "-nodisp", "-autoexit", filepath],
        ]
        
        for player_cmd in players:
            try:
                subprocess.run(
                    player_cmd, 
                    check=True,
                    capture_output=True,
                    timeout=120
                )
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
            except subprocess.TimeoutExpired:
                break
        
        logger.warning("No audio player worked")

    def stop(self):
        # Clear queue
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except:
                pass
        
        if self.pyttsx3_engine:
            self.pyttsx3_engine.stop()
