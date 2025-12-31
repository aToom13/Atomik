"""
Atomik Offline Computer Use - Element Detector
Uses OpenCV for UI element detection (buttons, inputs, icons).
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    """Represents a detected UI element"""
    element_type: str  # 'button', 'input', 'icon', 'text', 'unknown'
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    text: Optional[str] = None
    confidence: float = 1.0
    
    @property
    def center(self) -> Tuple[int, int]:
        """Return center coordinates"""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)
    
    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]
    
    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]


class ElementDetector:
    """
    OpenCV-based UI element detection.
    Combines contour detection, color analysis, and OCR for comprehensive detection.
    """
    
    def __init__(self):
        self.min_button_area = 500  # Minimum area for button detection
        self.max_button_area = 100000  # Maximum area
        
        # Common button colors (BGR format)
        self.button_colors = {
            'blue': ([100, 50, 0], [130, 255, 255]),    # HSV range
            'green': ([35, 50, 50], [85, 255, 255]),
            'red': ([0, 50, 50], [10, 255, 255]),
            'gray': ([0, 0, 100], [180, 30, 200]),
        }
    
    def find_buttons(self, image: np.ndarray) -> List[UIElement]:
        """
        Detect rectangular button-like elements.
        
        Uses contour detection + aspect ratio filtering.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Dilate to connect broken edges
        kernel = np.ones((3, 3), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        buttons = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_button_area < area < self.max_button_area:
                # Get bounding rectangle
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filter by aspect ratio (buttons are usually wider than tall or square-ish)
                aspect_ratio = w / h if h > 0 else 0
                if 0.3 < aspect_ratio < 10:  # Reasonable button proportions
                    # Check if it's roughly rectangular
                    epsilon = 0.02 * cv2.arcLength(contour, True)
                    approx = cv2.approxPolyDP(contour, epsilon, True)
                    
                    if 4 <= len(approx) <= 8:  # Roughly rectangular
                        buttons.append(UIElement(
                            element_type='button',
                            bbox=(x, y, x + w, y + h),
                            confidence=0.7
                        ))
        
        return buttons
    
    def find_input_fields(self, image: np.ndarray) -> List[UIElement]:
        """
        Detect text input fields.
        
        Input fields are typically:
        - Rectangular with thin borders
        - Wider than tall
        - Light/white background
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Threshold to find light regions (input fields usually white/light)
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        inputs = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            
            # Input fields are typically wider than tall
            aspect_ratio = w / h if h > 0 else 0
            
            if 2000 < area < 50000 and aspect_ratio > 2:
                inputs.append(UIElement(
                    element_type='input',
                    bbox=(x, y, x + w, y + h),
                    confidence=0.6
                ))
        
        return inputs
    
    def find_colored_elements(self, image: np.ndarray, 
                              color_name: str = 'blue') -> List[UIElement]:
        """
        Find UI elements of a specific color (e.g., blue buttons).
        """
        if color_name not in self.button_colors:
            return []
        
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower, upper = self.button_colors[color_name]
        
        # Create mask for the color
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        
        # Find contours in mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        elements = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_button_area:
                x, y, w, h = cv2.boundingRect(contour)
                elements.append(UIElement(
                    element_type=f'{color_name}_button',
                    bbox=(x, y, x + w, y + h),
                    confidence=0.8
                ))
        
        return elements
    
    def find_element_at_position(self, image: np.ndarray, 
                                  x: int, y: int) -> Optional[UIElement]:
        """
        Find the UI element at a specific position.
        Useful for understanding what's at cursor location.
        """
        all_elements = self.find_buttons(image) + self.find_input_fields(image)
        
        for element in all_elements:
            x1, y1, x2, y2 = element.bbox
            if x1 <= x <= x2 and y1 <= y <= y2:
                return element
        
        return None
    
    def find_clickable_near_text(self, image: np.ndarray, 
                                  text_bbox: Tuple[int, int, int, int],
                                  search_radius: int = 50) -> Optional[UIElement]:
        """
        Find a clickable element near a text block.
        
        Useful for finding buttons associated with labels.
        """
        text_center_x = (text_bbox[0] + text_bbox[2]) // 2
        text_center_y = (text_bbox[1] + text_bbox[3]) // 2
        
        all_buttons = self.find_buttons(image)
        
        closest = None
        min_distance = float('inf')
        
        for button in all_buttons:
            btn_center = button.center
            distance = ((btn_center[0] - text_center_x) ** 2 + 
                       (btn_center[1] - text_center_y) ** 2) ** 0.5
            
            if distance < min_distance and distance < search_radius:
                min_distance = distance
                closest = button
        
        return closest


# Global instance
_detector: Optional[ElementDetector] = None

def get_element_detector() -> ElementDetector:
    """Get or create global element detector instance"""
    global _detector
    if _detector is None:
        _detector = ElementDetector()
    return _detector
