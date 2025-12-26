"""
Atomik Core Module
"""
import os
import sys

# Ensure project root is in path BEFORE any imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from .config import (
    API_KEY, FORMAT, CHANNELS, SEND_SAMPLE_RATE, RECEIVE_SAMPLE_RATE,
    CHUNK_SIZE, MODEL, VAD_THRESHOLD, SILENCE_DURATION, FRAME_INTERVAL,
    SPEECH_FRAME_INTERVAL, SYSTEM_PROMPT
)
from .colors import Colors, print_header
from . import state
