"""
Atomik Audio Module
"""
import os
import sys

# Ensure project root is in path BEFORE any imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from .loop import AudioLoop, cleanup
from .video import capture_frames
