import whisper
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("downloader")

def download():
    print("Downloading Whisper model 'medium'...")
    try:
        # Download 'small' model as requested for speed.
        # Use CPU for download verification to avoid OOM if Ollama is running.
        model = whisper.load_model("small", device="cpu")
        print("Download complete!")
    except Exception as e:
        print(f"Error downloading: {e}")

if __name__ == "__main__":
    download()
