"""
Echo Cancellation Module v10 - Latency-Aware Smart Ducking
Optimized for larger buffer sizes (2048 samples) and high latency systems.
Uses a 'Soft Ducking' approach to prevent audio dropouts while suppressing echo.
"""
import time
import numpy as np
from collections import deque

class AcousticEchoCanceller:
    """
    Latency-Aware Smart Ducking.
    Designed to work with larger chunk sizes (reduced CPU load) and ALSA underruns.
    """
    
    def __init__(self, 
                 attenuation_level: float = 0.0,  # Full mute during playback (no echo at all)
                 holdoff_ms: int = 800,           # Longer holdoff for echo tail
                 barge_in_ratio: float = 0.5):    # User needs to be > 50% of speaker vol for barge-in
        
        self.attenuation_level = attenuation_level
        self.holdoff_ms = holdoff_ms
        self.barge_in_ratio = barge_in_ratio
        
        self._last_speaker_time: float = 0
        self._current_speaker_rms: float = 0
        # Use simple variable instead of deque for absolute max performance
        
    def feed_speaker(self, audio_data: bytes):
        """
        Register that speaker is outputting audio.
        """
        self._last_speaker_time = time.time()
        
        # Ultra fast RMS estimation (just peek at start/mid/end)
        # Avoid full numpy conversion if possible, but we need amplitude
        try:
            # Taking a strided slice is very fast in numpy
            # audio_data is bytes (int16)
            # Create numpy array from buffer (no copy)
            samples = np.frombuffer(audio_data, dtype=np.int16)
            
            # Simple peak-based estimation (faster than RMS)
            # We just need to know "is it loud?"
            peak = np.max(np.abs(samples[::10])) # Check every 10th sample
            self._current_speaker_rms = float(peak)
            
        except Exception:
            pass
    
    def _is_suppression_active(self) -> bool:
        """Check if we are in the suppression window."""
        if self._last_speaker_time == 0:
            return False
            
        elapsed = (time.time() - self._last_speaker_time) * 1000
        return elapsed < self.holdoff_ms
    
    def process_microphone(self, audio_data: bytes) -> bytes:
        """
        Apply soft ducking if speaker is active, unless user acts loud (Barge-In).
        """
        if not self._is_suppression_active():
            return audio_data
        
        try:
            # Mic analysis
            samples = np.frombuffer(audio_data, dtype=np.int16)
            
            # Fast peak detection for mic
            mic_peak = np.max(np.abs(samples[::4]))
            
            # Threshold Calculation
            # Dynamic threshold based on speaker volume
            threshold = self._current_speaker_rms * self.barge_in_ratio
            
            # Safety clamp: threshold shouldn't be too low (noise floor)
            threshold = max(threshold, 300) 
            
            # Barge-in Check
            if mic_peak > threshold:
                # User is speaking!
                return audio_data
            
            # Echo Suppression
            # Apply gain reduction (Ducking)
            # Efficient integer math
            # Convert to float for multiplication, then back? 
            # Or just right shift? 
            # Multiplication is fine on modern CPUs.
            
            # Create a writeable copy to modify
            suppressed = (samples * self.attenuation_level).astype(np.int16)
            return suppressed.tobytes()
            
        except Exception:
            return audio_data

# Global instance
aec = AcousticEchoCanceller()
