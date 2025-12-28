"""
Vision Analyzer - Background AI for frame comparison
Compares current frame with previous frame and detects significant changes.
Decides whether an event requires immediate interaction or just memory logging.
"""
import asyncio
import base64
import json
from google import genai

# Initialize Gemini client for vision analysis
try:
    from core.config import API_KEY
    vision_client = genai.Client(api_key=API_KEY)
    VISION_AVAILABLE = True
except Exception as e:
    print(f"Vision analyzer init error: {e}")
    VISION_AVAILABLE = False

# Store previous frame
_previous_frame = None

# Detailed prompt explaining the analyzer's role
import os

# Load prompt from file
try:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # core -> root
    prompt_path = os.path.join(base_dir, "AtomBase", "prompts", "vision_analyzer.txt")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        ANALYZER_PROMPT = f.read()
except Exception as e:
    print(f"Warning: Could not load vision prompt from file: {e}")
    # Fallback prompt (Minimal version to avoid crash)
    ANALYZER_PROMPT = """Sen arka planda çalışan "Gözlemci" yapay zekasın.
    Görevin: İki görüntüyü karşılaştırıp değişiklikleri analiz etmek.
    SADECE JSON döndür: { "type": "NONE" } (Fallback)"""



async def analyze_change(current_frame_payload: dict) -> dict:
    """
    Compare current frame with previous frame.
    Returns: Dict with type (INTERACTION, MEMORY, NONE) and description.
    """
    global _previous_frame
    
    if not VISION_AVAILABLE:
        return {"type": "NONE"}
    
    try:
        current_data = current_frame_payload.get('data', b'')
        current_mime = current_frame_payload.get('mime_type', 'image/jpeg')
        
        # If no previous frame, just store current and return
        if _previous_frame is None:
            _previous_frame = current_data
            return {"type": "NONE"}
        
        # Prepare images for Gemini
        prev_b64 = base64.b64encode(_previous_frame).decode('utf-8')
        curr_b64 = base64.b64encode(current_data).decode('utf-8')
        
        # Get learned rules and append to prompt
        from core.learning import get_formatted_rules
        final_prompt = ANALYZER_PROMPT + get_formatted_rules()
        
        # Call Gemini Vision API
        response = await asyncio.to_thread(
            vision_client.models.generate_content,
            model="gemini-3-flash-preview",
            contents=[
                {"role": "user", "parts": [
                    {"text": final_prompt},
                    {"inline_data": {"mime_type": current_mime, "data": prev_b64}},
                    {"inline_data": {"mime_type": current_mime, "data": curr_b64}}
                ]}
            ],
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        # Update previous frame
        _previous_frame = current_data
        
        # Parse JSON result
        try:
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            print(f"Vision analyzer JSON error: {response.text}")
            return {"type": "NONE"}
            
    except Exception as e:
        print(f"Vision analyzer error: {e}")
        # On error, update frame and return None
        _previous_frame = current_frame_payload.get('data', b'')
        return {"type": "NONE"}


def reset_previous_frame():
    """Reset the previous frame (useful when switching modes)"""
    global _previous_frame
    _previous_frame = None

async def find_element_on_screen(element_name: str, image_payload: dict) -> dict:
    """
    Locates a UI element on the screen using Gemini Vision.
    Returns: {"x": int, "y": int} coordinates (0-1000 range) or None.
    """
    if not VISION_AVAILABLE:
        return {"error": "Vision not available"}
        
    try:
        current_data = image_payload.get('data', b'')
        current_mime = image_payload.get('mime_type', 'image/jpeg')
        encoded_image = base64.b64encode(current_data).decode('utf-8')
        
        # Load prompt from file
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # core -> root
            prompt_path = os.path.join(base_dir, "AtomBase", "prompts", "computer_use.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                prompt_template = f.read()
            prompt = prompt_template.format(element_name=element_name)
        except Exception as e:
            # Fallback
            prompt = f"Ekranda '{element_name}' öğesini bul. Koordinatları ver."



        response = await asyncio.to_thread(
            vision_client.models.generate_content,
            model="gemini-2.5-computer-use-preview-10-2025",
            contents=[
                {"role": "user", "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": current_mime, "data": encoded_image}}
                ]}
            ],
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        return json.loads(response.text)
        
    except Exception as e:
        return {"error": str(e), "found": False}
