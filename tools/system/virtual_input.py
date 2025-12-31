"""
Unified Virtual Input Tool
Combines click, type, and key sending for virtual workspace.
"""
from tools.system.workspace import (
    click_in_workspace as _click,
    type_in_workspace as _type,
    send_key_in_workspace as _key,
    focus_window_in_workspace as _focus
)

def virtual_input(action: str, x: int = None, y: int = None, text: str = None, window: str = None) -> str:
    """
    Control the virtual workspace input.
    
    Args:
        action: 'click', 'type', 'key', or 'focus'
        x, y: Coordinates for click
        text: Text to type or key combo to send
        window: Window name to focus
        
    Returns:
        Status message
    """
    try:
        if action == "click":
            if x is None or y is None:
                return "❌ Click için X ve Y koordinatları gerekli."
            return _click(x, y)
            
        elif action == "type":
            if not text:
                return "❌ Yazılacak metin gerekli."
            return _type(text)
            
        elif action == "key":
            if not text:
                return "❌ Gönderilecek tuş kombinasyonu (text) gerekli."
            return _key(text)
            
        elif action == "focus":
            if not window:
                return "❌ Fokuslanacak pencere adı gerekli."
            return _focus(window)
            
        else:
            return f"❌ Bilinmeyen sanal input aksiyonu: {action}"
            
    except Exception as e:
        return f"❌ Sanal input hatası: {str(e)}"
