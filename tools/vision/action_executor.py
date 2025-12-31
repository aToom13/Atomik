"""
Atomik Offline Computer Use - Action Executor
PyAutoGUI-based mouse/keyboard actions with careful coordinate handling.
"""

import pyautogui
import time
from typing import Tuple, Optional, List
import logging

logger = logging.getLogger(__name__)

# Safety settings
pyautogui.FAILSAFE = True  # Move mouse to corner to abort
pyautogui.PAUSE = 0.1      # Small pause between actions


class ActionExecutor:
    """
    Executes mouse and keyboard actions with precise coordinate handling.
    
    COORDINATE HANDLING:
    - All coordinates are in screen pixels (absolute)
    - (0, 0) is top-left corner
    - Validates coordinates against screen bounds before action
    """
    
    def __init__(self):
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"ActionExecutor initialized. Screen: {self.screen_width}x{self.screen_height}")
    
    def _validate_coords(self, x: int, y: int) -> Tuple[int, int]:
        """
        Validate and clamp coordinates to screen bounds.
        
        Args:
            x, y: Target coordinates
            
        Returns:
            Validated (x, y) tuple clamped to screen bounds
        """
        # Clamp to screen bounds with small margin
        margin = 5
        x = max(margin, min(x, self.screen_width - margin))
        y = max(margin, min(y, self.screen_height - margin))
        return (int(x), int(y))
    
    def move_to(self, x: int, y: int, duration: float = 0.2) -> Tuple[int, int]:
        """
        Move mouse cursor to specified position.
        
        Args:
            x, y: Target coordinates
            duration: Movement duration in seconds
            
        Returns:
            Final (x, y) position
        """
        x, y = self._validate_coords(x, y)
        pyautogui.moveTo(x, y, duration=duration)
        logger.debug(f"Moved to ({x}, {y})")
        return (x, y)
    
    def click(self, x: int, y: int, button: str = 'left') -> Tuple[int, int]:
        """
        Move to position and click.
        
        Args:
            x, y: Click coordinates
            button: 'left', 'right', or 'middle'
            
        Returns:
            Click position
        """
        x, y = self._validate_coords(x, y)
        
        # Move first, then click (more reliable)
        pyautogui.moveTo(x, y, duration=0.15)
        time.sleep(0.05)  # Small delay for UI to register hover
        pyautogui.click(x, y, button=button)
        
        logger.info(f"Clicked ({x}, {y}) with {button} button")
        return (x, y)
    
    def double_click(self, x: int, y: int) -> Tuple[int, int]:
        """Double click at position"""
        x, y = self._validate_coords(x, y)
        pyautogui.moveTo(x, y, duration=0.15)
        pyautogui.doubleClick(x, y)
        logger.info(f"Double-clicked ({x}, {y})")
        return (x, y)
    
    def right_click(self, x: int, y: int) -> Tuple[int, int]:
        """Right click (context menu) at position"""
        return self.click(x, y, button='right')
    
    def type_text(self, text: str, interval: float = 0.02) -> None:
        """
        Type text character by character.
        
        Uses write() for natural typing.
        Falls back to hotkey for special characters.
        
        Args:
            text: Text to type
            interval: Delay between characters
        """
        # pyautogui.write doesn't support Turkish characters well
        # Use typewrite for ASCII, clipboard for others
        
        ascii_text = text.encode('ascii', 'ignore').decode()
        
        if ascii_text == text:
            # Pure ASCII, use normal typing
            pyautogui.write(text, interval=interval)
        else:
            # Has non-ASCII, use clipboard method
            import subprocess
            try:
                # Copy to clipboard using wl-copy or xclip
                subprocess.run(['wl-copy', text], check=True, timeout=1)
            except:
                try:
                    p = subprocess.Popen(['xclip', '-selection', 'clipboard'], 
                                        stdin=subprocess.PIPE)
                    p.communicate(input=text.encode('utf-8'))
                except:
                    logger.error("Could not copy text to clipboard")
                    return
            
            # Paste
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'v')
        
        logger.info(f"Typed: {text[:50]}{'...' if len(text) > 50 else ''}")
    
    def hotkey(self, *keys) -> None:
        """
        Press hotkey combination.
        
        Args:
            *keys: Key names (e.g., 'ctrl', 'shift', 'a')
        """
        pyautogui.hotkey(*keys)
        logger.info(f"Hotkey: {'+'.join(keys)}")
    
    def scroll(self, amount: int, x: Optional[int] = None, 
               y: Optional[int] = None) -> None:
        """
        Scroll at current or specified position.
        
        Args:
            amount: Positive = up, Negative = down
            x, y: Optional position to scroll at
        """
        if x is not None and y is not None:
            x, y = self._validate_coords(x, y)
            pyautogui.moveTo(x, y, duration=0.1)
        
        pyautogui.scroll(amount)
        logger.debug(f"Scrolled {amount}")
    
    def drag(self, start_x: int, start_y: int, 
             end_x: int, end_y: int, 
             duration: float = 0.3) -> None:
        """
        Drag from start to end position.
        """
        start_x, start_y = self._validate_coords(start_x, start_y)
        end_x, end_y = self._validate_coords(end_x, end_y)
        
        pyautogui.moveTo(start_x, start_y, duration=0.1)
        pyautogui.drag(end_x - start_x, end_y - start_y, 
                      duration=duration, button='left')
        logger.info(f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})")
    
    def wait(self, seconds: float) -> None:
        """Wait for specified duration"""
        time.sleep(seconds)
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """Get current mouse position"""
        return pyautogui.position()
    
    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None):
        """
        Take screenshot of screen or region.
        
        Args:
            region: Optional (x, y, width, height) tuple
            
        Returns:
            PIL Image
        """
        return pyautogui.screenshot(region=region)


# Global instance
_executor: Optional[ActionExecutor] = None

def get_action_executor() -> ActionExecutor:
    """Get or create global action executor instance"""
    global _executor
    if _executor is None:
        _executor = ActionExecutor()
    return _executor
