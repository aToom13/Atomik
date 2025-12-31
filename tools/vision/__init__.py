"""
Atomik Vision Package - Offline Computer Use

Provides OCR, UI element detection, and automated actions.

Usage:
    from tools.vision import get_screen_analyzer
    
    analyzer = get_screen_analyzer()
    success, msg = analyzer.find_and_click("Dosyalar")
"""

from .ocr_engine import OCREngine, TextBlock, get_ocr_engine
from .element_detector import ElementDetector, UIElement, get_element_detector
from .action_executor import ActionExecutor, get_action_executor
from .screen_analyzer import ScreenAnalyzer, ScreenState, get_screen_analyzer

__all__ = [
    # OCR
    'OCREngine', 'TextBlock', 'get_ocr_engine',
    # Element Detection
    'ElementDetector', 'UIElement', 'get_element_detector',
    # Actions
    'ActionExecutor', 'get_action_executor',
    # Unified Analyzer
    'ScreenAnalyzer', 'ScreenState', 'get_screen_analyzer',
]
