"""
Gesture Tool - Atomik's Body Control
AI can call this tool to express physical gestures through the avatar.
"""

# Tool definition for Gemini function calling
GESTURE_TOOL_DEFINITION = {
    "name": "express_gesture",
    "description": "Express a physical gesture or emotion through your avatar body language. Use this naturally during conversation - wave when greeting, nod when agreeing, think when pondering a question.",
    "parameters": {
        "type": "object",
        "properties": {
            "gesture": {
                "type": "string",
                "enum": ["wave", "nod", "shake_head", "smile", "think", "excited", "sad", "surprised"],
                "description": "The gesture to perform: wave (greeting), nod (agreement), shake_head (disagreement), smile (happiness), think (pondering), excited (enthusiasm), sad (empathy), surprised (astonishment)"
            },
            "intensity": {
                "type": "number",
                "description": "How pronounced the gesture should be, from 0.0 (subtle) to 1.0 (exaggerated). Default is 0.7"
            }
        },
        "required": ["gesture"]
    }
}


# Callback reference - set by gtk_app when avatar mode is active
_gesture_callback = None


def set_gesture_callback(callback):
    """
    Set the callback function that triggers avatar gestures.
    Called by gtk_app.py during initialization.
    """
    global _gesture_callback
    _gesture_callback = callback


def execute_gesture(gesture: str, intensity: float = 0.7) -> str:
    """
    Execute a gesture on the avatar.
    Called when AI uses the express_gesture tool.
    
    Returns:
        Status message for the AI
    """
    global _gesture_callback
    
    if _gesture_callback is None:
        return "Avatar mode not active - gesture not displayed"
    
    try:
        _gesture_callback(gesture, intensity)
        return f"Gesture '{gesture}' expressed with intensity {intensity}"
    except Exception as e:
        return f"Error expressing gesture: {e}"


def get_body_language_prompt() -> str:
    """
    Returns the body language instructions to add to Atomik's system prompt
    when avatar mode is active.
    """
    return """
## Vücut Dili (Avatar Modu)

Avatar modunda fiziksel bir vücudun var. Konuşurken doğal hareket et:

- **wave**: Selamlaşırken el salla
- **nod**: Onaylarken veya anladığını belirtirken başını salla
- **shake_head**: Hayır derken veya red ederken başını iki yana salla
- **smile**: Mutlu veya olumlu anlarda gülümse
- **think**: Düşünürken veya bir şeyi tarkarken düşünceli görün
- **excited**: Heyecanlı haberlerde veya başarılarda heyecanlan
- **sad**: Üzücü haberlerde veya empati kurarken üzgün görün
- **surprised**: Beklenmedik bir şey duyduğunda şaşır

express_gesture tool'unu **doğal anlarda** kullan, her cümlede değil. 
İnsan gibi davran - sürekli hareket eden biri değil, anlamlı anlarda jest yapan biri ol.

Örnek kullanımlar:
- "Merhaba!" derken → wave
- "Evet, anlıyorum" derken → nod
- "Hmm, bunu düşüneyim..." derken → think
- "Harika haber!" derken → excited + smile
"""
