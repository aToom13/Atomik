"""
Voice Recording Module - Records Atomik's voice output for WhatsApp
"""
import wave
import os
import tempfile
import time
from typing import Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class VoiceRecording:
    """Holds recorded audio data"""
    samples: bytearray
    sample_rate: int = 24000
    channels: int = 1
    sample_width: int = 2  # 16-bit

class VoiceRecorder:
    """Records Atomik's voice output from the audio queue"""
    
    def __init__(self, sample_rate: int = 24000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self._buffer = bytearray()
        self._last_recording_path: Optional[str] = None
        
        # Recording directory - save to workspace
        project_root = Path(__file__).parent.parent
        self.recording_dir = project_root / "atom_workspace" / "voice_recordings"
        self.recording_dir.mkdir(parents=True, exist_ok=True)
    
    def start_recording(self):
        """Start recording audio"""
        self._buffer = bytearray()
        self.is_recording = True
        print("🎙️ Ses kaydı başlatıldı...")
    
    def feed_audio(self, audio_data: bytes):
        """Feed audio data to the recorder (called from play_audio)"""
        if self.is_recording:
            self._buffer.extend(audio_data)
    
    def stop_recording(self) -> Optional[str]:
        """Stop recording and save to file, returns file path"""
        if not self.is_recording:
            return None
            
        self.is_recording = False
        
        if len(self._buffer) < 1000:  # Too short
            print("⚠️ Kayıt çok kısa, iptal edildi")
            return None
        
        # Generate unique filename
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        wav_path = self.recording_dir / f"atomik_voice_{timestamp}.wav"
        
        # Convert to MP3 (if ffmpeg available)
        try:
            self._save_wav(str(wav_path))
            
            # Try to convert to mp3
            mp3_path = wav_path.with_suffix(".mp3")
            
            import subprocess
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", str(wav_path), 
                 "-c:a", "libmp3lame", "-b:a", "128k",
                 str(mp3_path)],
                capture_output=True,
                timeout=30
            )
            
            if result.returncode == 0 and mp3_path.exists():
                # Remove wav, keep mp3
                wav_path.unlink()
                self._last_recording_path = str(mp3_path)
                print(f"✅ Ses kaydedildi: {mp3_path.name}")
                return str(mp3_path)
            else:
                # Keep wav if conversion failed
                self._last_recording_path = str(wav_path)
                print(f"✅ Ses kaydedildi (WAV): {wav_path.name}")
                return str(wav_path)
                
        except Exception as e:
            # Just save as wav
            self._save_wav(str(wav_path))
            self._last_recording_path = str(wav_path)
            print(f"✅ Ses kaydedildi: {wav_path.name}")
            return str(wav_path)
    
    def _save_wav(self, filepath: str):
        """Save buffer as WAV file"""
        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(bytes(self._buffer))
    
    def get_last_recording(self) -> Optional[str]:
        """Get path to the last recording"""
        return self._last_recording_path
    
    def clear(self):
        """Clear the buffer"""
        self._buffer = bytearray()
        self.is_recording = False


# Global singleton
_recorder: Optional[VoiceRecorder] = None

def get_voice_recorder() -> VoiceRecorder:
    """Get or create the global voice recorder"""
    global _recorder
    if _recorder is None:
        _recorder = VoiceRecorder(sample_rate=24000, channels=1)
    return _recorder
