import whisper
import os
import torch

def verify():
    print("Verifying 'small' model...")
    try:
        # Force CPU to check integrity without OOM
        model = whisper.load_model("small", device="cpu")
        print("SUCCESS: Model loaded correctly.")
    except Exception as e:
        print(f"FAILED: {e}")
        # If hash mismatch or EOF, it's corrupt.
        
if __name__ == "__main__":
    verify()
