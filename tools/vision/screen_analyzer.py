"""
Atomik Offline Computer Use - Screen Analyzer
Unified interface combining OCR, Element Detection, and Actions.
"""

import cv2
import numpy as np
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass
import logging
from PIL import Image
import io

from .ocr_engine import OCREngine, TextBlock, get_ocr_engine
from .element_detector import ElementDetector, UIElement, get_element_detector
from .action_executor import ActionExecutor, get_action_executor

logger = logging.getLogger(__name__)


@dataclass
class ScreenState:
    """Complete analysis of current screen state"""
    text_blocks: List[TextBlock]
    ui_elements: List[UIElement]
    screen_width: int
    screen_height: int
    
    def find_text(self, query: str) -> Optional[TextBlock]:
        """Find text block containing query"""
        query_lower = query.lower()
        for block in self.text_blocks:
            if query_lower in block.text.lower():
                return block
        return None
    
    def get_all_text(self) -> str:
        """Get all detected text as single string"""
        return " ".join(b.text for b in self.text_blocks)


class ScreenAnalyzer:
    """
    High-level screen analysis and interaction.
    
    Combines OCR, element detection, and actions into a unified interface.
    Designed for LLM-driven computer control.
    """
    
    def __init__(self):
        self.ocr = get_ocr_engine()
        self.detector = get_element_detector()
        self.executor = get_action_executor()
        self._last_screenshot = None
        self._last_state: Optional[ScreenState] = None
    
    def capture_screen(self) -> np.ndarray:
        """
        Capture full screen as OpenCV image.
        
        Returns:
            BGR numpy array
        """
        screenshot = self.executor.screenshot()
        
        # Convert PIL to OpenCV
        img_array = np.array(screenshot)
        # Convert RGB to BGR
        self._last_screenshot = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        return self._last_screenshot
    
    def analyze_screen(self, fresh: bool = True) -> ScreenState:
        """
        Full screen analysis: OCR + Element Detection.
        
        Args:
            fresh: Whether to capture new screenshot
            
        Returns:
            ScreenState with all detected elements
        """
        if fresh or self._last_screenshot is None:
            self.capture_screen()
        
        image = self._last_screenshot
        h, w = image.shape[:2]
        
        # Run OCR
        text_blocks = self.ocr.extract_text(image)
        
        # Detect UI elements
        buttons = self.detector.find_buttons(image)
        inputs = self.detector.find_input_fields(image)
        ui_elements = buttons + inputs
        
        self._last_state = ScreenState(
            text_blocks=text_blocks,
            ui_elements=ui_elements,
            screen_width=w,
            screen_height=h
        )
        
        return self._last_state
    
    def find_and_click(self, target_text: str, position_hint: str = None) -> Tuple[bool, str]:
        """
        Find text on screen and click it.
        
        Args:
            target_text: Text to find and click
            position_hint: Optional hint like 'sağ alt', 'sol üst', 'ortada'
            
        Returns:
            (success, message) tuple
        """
        # Capture and analyze
        self.capture_screen()
        h, w = self._last_screenshot.shape[:2]
        
        # Find ALL occurrences of the text
        all_matches = self.ocr.find_all_text(self._last_screenshot, target_text)
        
        if not all_matches:
            return False, f"'{target_text}' ekranda bulunamadı."
        
        # Filter by position hint if provided
        if position_hint:
            hint_lower = position_hint.lower()
            filtered = []
            
            for block in all_matches:
                cx, cy = block.center
                
                # Check vertical position
                is_top = cy < h * 0.4
                is_bottom = cy > h * 0.6
                is_vmid = h * 0.3 < cy < h * 0.7
                
                # Check horizontal position
                is_left = cx < w * 0.4
                is_right = cx > w * 0.6
                is_hmid = w * 0.3 < cx < w * 0.7
                
                # Match position hints
                match = True
                if 'alt' in hint_lower or 'aşağı' in hint_lower:
                    match = match and is_bottom
                if 'üst' in hint_lower or 'yukarı' in hint_lower:
                    match = match and is_top
                if 'sağ' in hint_lower:
                    match = match and is_right
                if 'sol' in hint_lower:
                    match = match and is_left
                if 'orta' in hint_lower:
                    match = match and (is_vmid or is_hmid)
                
                if match:
                    filtered.append(block)
            
            if filtered:
                all_matches = filtered
            # else: use all matches as fallback
        
        # Pick the best match (highest confidence, or if position filtered, the one closest to corner)
        if len(all_matches) == 1:
            best = all_matches[0]
        else:
            # Sort by confidence
            best = max(all_matches, key=lambda b: b.confidence)
        
        # Click center of text
        x, y = best.center
        self.executor.click(x, y)
        
        return True, f"'{target_text}' bulundu ({x}, {y}) ve tıklandı."
    
    def find_and_type(self, target_text: str, input_text: str) -> Tuple[bool, str]:
        """
        Find input field near text and type into it.
        
        Args:
            target_text: Label/placeholder to find
            input_text: Text to type
            
        Returns:
            (success, message) tuple
        """
        self.capture_screen()
        
        # Find label text
        label = self.ocr.find_text(self._last_screenshot, target_text)
        
        if label is None:
            # Maybe it's an input field itself, try direct click
            self.executor.hotkey('ctrl', 'a')  # Select all
            self.executor.type_text(input_text)
            return True, f"Aktif alana '{input_text}' yazıldı."
        
        # Look for input field near the label
        input_field = self.detector.find_clickable_near_text(
            self._last_screenshot, label.bbox, search_radius=100
        )
        
        if input_field:
            x, y = input_field.center
        else:
            # Click to the right of the label (common pattern)
            x = label.bbox[2] + 50  # Right of text
            y = label.center[1]      # Same vertical level
        
        # Click and type
        self.executor.click(x, y)
        self.executor.wait(0.1)
        self.executor.type_text(input_text)
        
        return True, f"'{target_text}' yanına '{input_text}' yazıldı."
    
    def open_app_search(self) -> None:
        """Open application search (Ctrl+Space or Super key)"""
        self.executor.hotkey('ctrl', 'space')
        self.executor.wait(0.3)
    
    def open_application(self, app_name: str) -> Tuple[bool, str]:
        """
        Open an application by name.
        
        Uses app search (Ctrl+Space) then types and clicks.
        """
        # Open search
        self.open_app_search()
        
        # Type app name
        self.executor.type_text(app_name)
        self.executor.wait(0.5)
        
        # Capture and find result
        self.capture_screen()
        result = self.ocr.find_text(self._last_screenshot, app_name)
        
        if result:
            self.executor.click(*result.center)
            return True, f"'{app_name}' açıldı."
        else:
            # Just press Enter (first result)
            self.executor.hotkey('return')
            return True, f"'{app_name}' için Enter basıldı."
    
    def read_screen(self) -> str:
        """
        Read all text on screen.
        
        Returns:
            All detected text as single string
        """
        state = self.analyze_screen(fresh=True)
        return state.get_all_text()
    
    def get_screen_summary(self) -> Dict:
        """
        Get summary of screen for LLM context.
        
        Returns:
            Dict with text_count, element_count, and sample texts
        """
        state = self.analyze_screen(fresh=True)
        
        # Get top 10 most confident text blocks
        sorted_blocks = sorted(state.text_blocks, 
                              key=lambda b: b.confidence, reverse=True)[:10]
        
        return {
            "text_count": len(state.text_blocks),
            "button_count": sum(1 for e in state.ui_elements if 'button' in e.element_type),
            "input_count": sum(1 for e in state.ui_elements if e.element_type == 'input'),
            "sample_texts": [b.text for b in sorted_blocks],
            "screen_size": f"{state.screen_width}x{state.screen_height}"
        }
    
    def smart_find_and_click(self, description: str) -> Tuple[bool, str]:
        """
        Intelligent element finding using color + OCR + LLM.
        
        Args:
            description: Natural language description like "mavi Accept All butonu"
            
        Returns:
            (success, message) tuple
        """
        self.capture_screen()
        h, w = self._last_screenshot.shape[:2]
        desc_lower = description.lower()
        
        # Step 1: Extract hints from description
        color_hint = None
        for color in ['mavi', 'kırmızı', 'yeşil', 'gri', 'blue', 'red', 'green', 'gray']:
            if color in desc_lower:
                color_map = {'mavi': 'blue', 'kırmızı': 'red', 'yeşil': 'green', 'gri': 'gray'}
                color_hint = color_map.get(color, color)
                break
        
        position_hint = None
        for pos in ['sağ', 'sol', 'üst', 'alt', 'altta', 'ortada']:
            if pos in desc_lower:
                position_hint = (position_hint or "") + " " + pos
        
        # Extract text to find (remove color and position words)
        text_hint = description
        for remove in ['mavi', 'kırmızı', 'yeşil', 'gri', 'blue', 'red', 'green', 'gray',
                       'sağ', 'sol', 'üst', 'alt', 'altta', 'ortada',
                       'butona', 'buton', 'butonu', 'tıkla', 'yazısına', 'yazan']:
            text_hint = text_hint.replace(remove, '')
        text_hint = ' '.join(text_hint.split()).strip()
        
        candidates = []
        
        # Step 2: Find colored elements if color specified
        if color_hint:
            colored_elements = self.detector.find_colored_elements(self._last_screenshot, color_hint)
            for elem in colored_elements:
                # Get text inside this element using OCR
                x1, y1, x2, y2 = elem.bbox
                region = self._last_screenshot[y1:y2, x1:x2]
                if region.size > 0:
                    texts = self.ocr.extract_text(region)
                    elem_text = ' '.join(t.text for t in texts)
                    candidates.append({
                        'type': f'{color_hint}_button',
                        'bbox': elem.bbox,
                        'center': elem.center,
                        'text': elem_text,
                        'score': 0.8  # Color match bonus
                    })
        
        # Step 3: Find text matches with OCR
        if text_hint:
            text_matches = self.ocr.find_all_text(self._last_screenshot, text_hint)
            for block in text_matches:
                # Check if this text is inside a colored region
                cx, cy = block.center
                is_in_color_region = any(
                    c['bbox'][0] <= cx <= c['bbox'][2] and c['bbox'][1] <= cy <= c['bbox'][3]
                    for c in candidates
                )
                
                candidates.append({
                    'type': 'text',
                    'bbox': block.bbox,
                    'center': block.center,
                    'text': block.text,
                    'score': 0.7 + (0.2 if is_in_color_region else 0)
                })
        
        if not candidates:
            return False, f"'{description}' ile eşleşen element bulunamadı."
        
        # Step 4: Filter by position
        if position_hint:
            filtered = []
            for c in candidates:
                cx, cy = c['center']
                match = True
                if 'alt' in position_hint: match = match and cy > h * 0.6
                if 'üst' in position_hint: match = match and cy < h * 0.4
                if 'sağ' in position_hint: match = match and cx > w * 0.6
                if 'sol' in position_hint: match = match and cx < w * 0.4
                if match:
                    filtered.append(c)
            if filtered:
                candidates = filtered
        
        # Step 5: Use LLM to pick best candidate if multiple matches
        if len(candidates) > 1:
            # Build context for LLM
            context = f"Kullanıcı '{description}' elementine tıklamak istiyor.\n"
            context += "Bulunan adaylar:\n"
            for i, c in enumerate(candidates[:5]):  # Max 5
                context += f"{i+1}. {c['type']} - '{c['text'][:30]}' @ ({c['center'][0]}, {c['center'][1]})\n"
            context += "\nHangisi doğru seçenek? Sadece numara yaz."
            
            try:
                from tools.llm.ollama_client import OllamaClient
                client = OllamaClient()
                response = client.generate_text(context)
                
                # Extract number from response
                import re
                num_match = re.search(r'(\d+)', response)
                if num_match:
                    idx = int(num_match.group(1)) - 1
                    if 0 <= idx < len(candidates):
                        best = candidates[idx]
                    else:
                        best = max(candidates, key=lambda c: c['score'])
                else:
                    best = max(candidates, key=lambda c: c['score'])
            except:
                best = max(candidates, key=lambda c: c['score'])
        else:
            best = candidates[0]
        
        # Step 6: Click
        x, y = best['center']
        self.executor.click(x, y)
        
        return True, f"'{best['text'][:20]}' ({best['type']}) bulundu ({x}, {y}) ve tıklandı."
    
    def click_by_region(self, description: str) -> Tuple[bool, str]:
        """
        Click based on position description alone (no text matching).
        
        For descriptions like "sağ üstte kontrol paneli"
        where there's no text to match, just a region to click.
        
        Args:
            description: Natural language position description
            
        Returns:
            (success, message) tuple
        """
        self.capture_screen()
        h, w = self._last_screenshot.shape[:2]
        desc_lower = description.lower()
        
        # Default to center
        x, y = w // 2, h // 2
        
        # Parse position hints
        if 'sağ' in desc_lower:
            x = int(w * 0.9)
        elif 'sol' in desc_lower:
            x = int(w * 0.1)
        
        if 'üst' in desc_lower or 'yukarı' in desc_lower:
            y = int(h * 0.05)  # Very top (system tray area)
        elif 'alt' in desc_lower or 'aşağı' in desc_lower:
            y = int(h * 0.95)
        
        # Special cases for common UI areas
        if 'kontrol paneli' in desc_lower or 'sistem tepsisi' in desc_lower or 'system tray' in desc_lower:
            # GNOME system tray is usually top-right corner
            x = int(w * 0.95)
            y = int(h * 0.02)
        elif 'uygulama menü' in desc_lower or 'activities' in desc_lower or 'overview' in desc_lower:
            # GNOME activities is top-left
            x = int(w * 0.02)
            y = int(h * 0.02)
        elif 'dock' in desc_lower or 'görev çubuğu' in desc_lower:
            # Usually bottom or left
            x = w // 2
            y = int(h * 0.98)
        elif 'kapat' in desc_lower or 'close' in desc_lower:
            # Close button usually top-right of focused window
            x = int(w * 0.98)
            y = int(h * 0.05)
        
        self.executor.click(x, y)
        return True, f"'{description}' için bölgeye ({x}, {y}) tıklandı."
    
    def comprehensive_click(self, description: str) -> Tuple[bool, str]:
        """
        Try all methods to click on described element.
        
        Order:
        1. smart_find_and_click (color + OCR + LLM)
        2. find_and_click (basic OCR)
        3. click_by_region (position only)
        """
        desc_lower = description.lower()
        
        # Check if has color hint -> use smart_find_and_click
        color_keywords = ['mavi', 'kırmızı', 'yeşil', 'gri', 'blue', 'red', 'green', 'gray']
        has_color = any(c in desc_lower for c in color_keywords)
        
        if has_color:
            success, msg = self.smart_find_and_click(description)
            if success:
                return success, msg
        
        # Try basic OCR with position hints
        # Extract text to search for
        text_hint = description
        for remove in ['sağ', 'sol', 'üst', 'alt', 'altta', 'ortada', 'köşede',
                       'tıkla', 'bas', 'butonuna', 'butona', 'menüsüne', 'menüsü']:
            text_hint = text_hint.replace(remove, '')
        text_hint = ' '.join(text_hint.split()).strip()
        
        if text_hint:
            # Extract position hint
            position_hint = None
            for pos in ['sağ', 'sol', 'üst', 'alt']:
                if pos in desc_lower:
                    position_hint = (position_hint or "") + " " + pos
            
            success, msg = self.find_and_click(text_hint, position_hint=position_hint)
            if success:
                return success, msg
        
        # Fallback to region-based click
        return self.click_by_region(description)


# Global instance
_analyzer: Optional[ScreenAnalyzer] = None

def get_screen_analyzer() -> ScreenAnalyzer:
    """Get or create global screen analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = ScreenAnalyzer()
    return _analyzer
