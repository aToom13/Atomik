import os
import logging
import numpy as np

logger = logging.getLogger("atomik.audio.stt")

# Try Faster-Whisper first (recommended)
try:
    from faster_whisper import WhisperModel
    FASTER_WHISPER_AVAILABLE = True
except ImportError:
    FASTER_WHISPER_AVAILABLE = False

# Fallback to openai-whisper
try:
    import whisper
    import torch
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

class OfflineSTT:
    def __init__(self, model_size="medium"):
        self.model = None
        self.model_size = model_size
        self.use_faster_whisper = False
        
        # Try Faster-Whisper first (4-6x faster, less VRAM)
        if FASTER_WHISPER_AVAILABLE:
            try:
                logger.info(f"Loading Faster-Whisper model '{model_size}'...")
                # Use CPU to avoid cuDNN version mismatch issues
                # int8 quantization for efficiency
                compute_type = "int8"
                device = "cpu"  # Force CPU - cuDNN 9.x often not installed
                
                self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
                
                self.use_faster_whisper = True
                logger.info(f"Faster-Whisper Ready ({model_size}, CPU, {compute_type})")
                return
                
            except Exception as e:
                logger.warning(f"Faster-Whisper failed: {e}")
        
        # Fallback to standard Whisper
        if WHISPER_AVAILABLE:
            try:
                device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info(f"Loading Whisper model '{model_size}' on {device}...")
                
                try:
                    self.model = whisper.load_model(model_size, device=device)
                except Exception as e:
                    if "out of memory" in str(e).lower():
                        logger.warning(f"GPU OOM. Falling back to CPU.")
                        self.model = whisper.load_model(model_size, device="cpu")
                    else:
                        logger.warning(f"Model '{model_size}' error: {e}. Fallback to 'small'.")
                        self.model = whisper.load_model("small", device="cpu")
                
                logger.info("Whisper STT Ready.")
                
            except Exception as e:
                logger.error(f"Failed to init STT: {e}")
        else:
            logger.error("No STT engine available. Install faster-whisper or openai-whisper.")

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio chunk"""
        if not self.model:
            return ""

        try:
            # Ensure float32 audio
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32) / 32768.0
            
            if self.use_faster_whisper:
                # Faster-Whisper API
                segments, info = self.model.transcribe(
                    audio_data, 
                    language="tr",
                    beam_size=5,
                    vad_filter=True  # Voice Activity Detection
                )
                text = " ".join([segment.text for segment in segments]).strip()
            else:
                # Standard Whisper API
                result = self.model.transcribe(audio_data, language="tr", fp16=False)
                text = result.get("text", "").strip()
            
            return text
            
        except Exception as e:
            logger.error(f"Transcribe error: {e}")
            return ""
