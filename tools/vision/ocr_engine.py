"""
Atomik Offline Computer Use - OCR Engine
Uses EasyOCR with careful coordinate extraction for UI element detection.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class TextBlock:
    """Represents a detected text block with its bounding box"""
    text: str
    # Bounding box: (x1, y1, x2, y2) - top-left and bottom-right corners
    bbox: Tuple[int, int, int, int]
    confidence: float
    
    @property
    def center(self) -> Tuple[int, int]:
        """Return center coordinates of the text block"""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)
    
    @property
    def width(self) -> int:
        return self.bbox[2] - self.bbox[0]
    
    @property
    def height(self) -> int:
        return self.bbox[3] - self.bbox[1]


class OCREngine:
    """
    EasyOCR-based text extraction with precise coordinate mapping.
    Designed for UI element detection in offline computer use.
    """
    
    def __init__(self, languages: List[str] = ['tr', 'en']):
        """
        Initialize OCR engine with specified languages.
        
        Args:
            languages: List of language codes (default: Turkish + English)
        """
        self.reader = None
        self.languages = languages
        self._lazy_load()
    
    def _lazy_load(self):
        """Lazy load EasyOCR to avoid startup delay"""
        if self.reader is None:
            try:
                import easyocr
                # Force CPU mode to avoid GPU memory conflicts with Ollama
                self.reader = easyocr.Reader(
                    self.languages,
                    gpu=False,  # CPU mode - GPU reserved for LLM
                    verbose=False
                )
                logger.info(f"EasyOCR loaded with languages: {self.languages}")
            except ImportError:
                logger.error("EasyOCR not installed. Run: pip install easyocr")
                raise
            except Exception as e:
                logger.warning(f"GPU not available, falling back to CPU: {e}")
                import easyocr
                self.reader = easyocr.Reader(self.languages, gpu=False, verbose=False)
    
    def extract_text(self, image: np.ndarray) -> List[TextBlock]:
        """
        Extract all text from image with bounding boxes.
        
        Args:
            image: OpenCV image (BGR format) or numpy array
            
        Returns:
            List of TextBlock objects with text, bbox, and confidence
        """
        if self.reader is None:
            self._lazy_load()
        
        # Convert BGR to RGB if needed
        if len(image.shape) == 3 and image.shape[2] == 3:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb_image = image
        
        # Run OCR
        results = self.reader.readtext(rgb_image)
        
        text_blocks = []
        for (bbox_points, text, confidence) in results:
            # EasyOCR returns 4 corner points, we need top-left and bottom-right
            # bbox_points = [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
            x_coords = [int(p[0]) for p in bbox_points]
            y_coords = [int(p[1]) for p in bbox_points]
            
            x1, y1 = min(x_coords), min(y_coords)
            x2, y2 = max(x_coords), max(y_coords)
            
            text_blocks.append(TextBlock(
                text=text.strip(),
                bbox=(x1, y1, x2, y2),
                confidence=confidence
            ))
        
        return text_blocks
    
    def find_text(self, image: np.ndarray, target: str, 
                  case_sensitive: bool = False,
                  threshold: float = 0.5) -> Optional[TextBlock]:
        """
        Find specific text in image and return its location.
        
        Args:
            image: OpenCV image
            target: Text to search for
            case_sensitive: Whether to match case
            threshold: Minimum confidence threshold
            
        Returns:
            TextBlock if found, None otherwise
        """
        text_blocks = self.extract_text(image)
        
        search_target = target if case_sensitive else target.lower()
        
        for block in text_blocks:
            block_text = block.text if case_sensitive else block.text.lower()
            
            # Exact match or contains
            if search_target in block_text and block.confidence >= threshold:
                return block
        
        return None
    
    def find_all_text(self, image: np.ndarray, target: str,
                      case_sensitive: bool = False) -> List[TextBlock]:
        """Find all occurrences of target text"""
        text_blocks = self.extract_text(image)
        
        search_target = target if case_sensitive else target.lower()
        matches = []
        
        for block in text_blocks:
            block_text = block.text if case_sensitive else block.text.lower()
            if search_target in block_text:
                matches.append(block)
        
        return matches
    
    def get_text_at_region(self, image: np.ndarray, 
                           x: int, y: int, w: int, h: int) -> str:
        """
        Extract text from a specific region of the image.
        
        Args:
            image: Full screen image
            x, y: Top-left corner of region
            w, h: Width and height of region
            
        Returns:
            Concatenated text from the region
        """
        # Crop region
        region = image[y:y+h, x:x+w]
        
        # Extract text
        text_blocks = self.extract_text(region)
        
        # Sort by Y then X for reading order
        text_blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
        
        return " ".join(block.text for block in text_blocks)


# Global instance for reuse
_ocr_engine: Optional[OCREngine] = None

def get_ocr_engine() -> OCREngine:
    """Get or create global OCR engine instance"""
    global _ocr_engine
    if _ocr_engine is None:
        _ocr_engine = OCREngine()
    return _ocr_engine
