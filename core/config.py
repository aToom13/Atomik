"""
Atomik Core Configuration
"""
import os
import sys
from dotenv import load_dotenv
import pyaudio

# Load environment variables
load_dotenv()

# API Key
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    print("HATA: GEMINI_API_KEY veya GOOGLE_API_KEY ayarlanmamış!")
    print("Lütfen .env dosyasına ekleyin: GEMINI_API_KEY=your_key_here")
    sys.exit(1)

# Audio Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# Model
MODEL = "models/gemini-2.5-flash-native-audio-preview-12-2025"

# VAD Settings
VAD_THRESHOLD = 600
SILENCE_DURATION = 0.5
FRAME_INTERVAL = 1.0
SPEECH_FRAME_INTERVAL = 3

# Load system prompt
def load_system_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "AtomBase", "prompts", "supervisor.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return "Sen Atomik, yardımcı bir asistansın. Türkçe konuş."

SYSTEM_PROMPT = load_system_prompt()
