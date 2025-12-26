"""
Computer Control Module
Allows Atomik to control mouse and keyboard using xdotool.
"""
import subprocess
import shutil

XDO_PATH = shutil.which("xdotool")

def is_available() -> bool:
    return XDO_PATH is not None

def execute_xdo(args: list) -> str:
    if not is_available():
        return "Error: xdotool not installed."
    
    try:
        cmd = [XDO_PATH] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return "Success"
        else:
            return f"Error: {result.stderr.strip()}"
    except Exception as e:
        return f"Exception: {e}"

def mouse_move(x: int, y: int) -> str:
    """Move mouse to x, y coordinates."""
    return execute_xdo(["mousemove", str(x), str(y)])

def mouse_click(button: int = 1, x: int = None, y: int = None) -> str:
    """Click mouse button (1=left, 2=middle, 3=right). Optionally move first."""
    if x is not None and y is not None:
        # Move first
        res = mouse_move(x, y)
        if "Error" in res: return res
        
    return execute_xdo(["click", str(button)])

def keyboard_type(text: str) -> str:
    """Type text with a small delay between keystrokes to ensure registration."""
    # --delay 100 adds 100ms between keystrokes
    return execute_xdo(["type", "--delay", "100", text])

def keyboard_key(key: str) -> str:
    """Press a specific key. waits 0.5s after to allow UI to react."""
    import time
    
    # Map common aliases to xdotool names
    key_map = {
        "enter": "Return",
        "esc": "Escape",
        "backspace": "BackSpace"
    }
    key = key_map.get(key.lower(), key)
    
    res = execute_xdo(["key", key])
    time.sleep(0.5) # Wait for UI (like launchers) to appear
    return res

def get_screen_size() -> str:
    """Get screen dimensions."""
    # xdotool doesn't directly give screen size easily without parsing scripts.
    # We can use xrandr if available, or just rely on relative moves if needed.
    # Let's try xdpyinfo or similar if needed, but for now just return unknown or maybe xdotool getdisplaygeometry
    try:
        cmd = [XDO_PATH, "getdisplaygeometry"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return "Unknown"
