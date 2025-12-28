"""
Unified Vision - Tek Birleşik Görme Aracı
==========================================
Tüm görme yeteneklerini tek bir akıllı araçta birleştirir:
- Ekran analizi
- Metin okuma (OCR)
- UI element bulma
- Zoom/region desteği
"""
import os
import sys
import json
import base64
import logging
from typing import Dict, Optional, Tuple, List
from io import BytesIO

# Project root
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

logger = logging.getLogger("atomik.unified_vision")

# Gemini client
try:
    from google import genai
    from core.config import API_KEY
    _client = genai.Client(api_key=API_KEY)
    GENAI_AVAILABLE = True
except ImportError:
    _client = None
    GENAI_AVAILABLE = False
    logger.warning("Gemini API not available for UnifiedVision")


# ============================================================================
# REGION DEFINITIONS
# ============================================================================
REGIONS = {
    # Ana bölgeler
    "üst": (0, 0, 1, 0.33),
    "orta": (0, 0.33, 1, 0.66),
    "alt": (0, 0.66, 1, 1),
    "sol": (0, 0, 0.5, 1),
    "sağ": (0.5, 0, 1, 1),
    "merkez": (0.25, 0.25, 0.75, 0.75),
    
    # Köşeler
    "üst-sol": (0, 0, 0.5, 0.33),
    "üst-sağ": (0.5, 0, 1, 0.33),
    "alt-sol": (0, 0.66, 0.5, 1),
    "alt-sağ": (0.5, 0.66, 1, 1),
    
    # Detaylı bölgeler
    "navbar": (0, 0, 1, 0.1),
    "sidebar-sol": (0, 0, 0.2, 1),
    "sidebar-sağ": (0.8, 0, 1, 1),
    "içerik": (0.2, 0.1, 0.8, 0.9),
}


# ============================================================================
# PROMPT LOADING FROM FILE
# ============================================================================
def _load_prompts():
    """Load prompts from AtomBase/prompts/unified_vision.txt"""
    prompts = {
        "general": "",
        "read": "",
        "find": ""
    }
    
    try:
        prompt_path = os.path.join(_project_root, "AtomBase", "prompts", "unified_vision.txt")
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Parse prompts from file
        import re
        
        # Extract PROMPT_GENERAL
        match = re.search(r'PROMPT_GENERAL\s*=\s*"""(.+?)"""', content, re.DOTALL)
        if match:
            prompts["general"] = match.group(1).strip()
        
        # Extract PROMPT_READ
        match = re.search(r'PROMPT_READ\s*=\s*"""(.+?)"""', content, re.DOTALL)
        if match:
            prompts["read"] = match.group(1).strip()
        
        # Extract PROMPT_FIND
        match = re.search(r'PROMPT_FIND\s*=\s*"""(.+?)"""', content, re.DOTALL)
        if match:
            prompts["find"] = match.group(1).strip()
            
        logger.info("Prompts loaded from unified_vision.txt")
        
    except Exception as e:
        logger.warning(f"Could not load prompts from file: {e}")
        # Fallback prompts
        prompts["general"] = "Ekranı analiz et. JSON döndür: {\"application\": \"?\", \"activity\": \"?\"}"
        prompts["read"] = "Ekrandaki metinleri oku. JSON döndür: {\"all_text\": \"?\", \"urls\": []}"
        prompts["find"] = "'{element}' elementini bul. JSON döndür: {\"found\": false}"
    
    return prompts

# Load prompts at module import
_PROMPTS = _load_prompts()


# ============================================================================
# MAIN FUNCTION
# ============================================================================
def see_screen(
    task: str = None,
    region: str = None,
    find: str = None
) -> Dict:
    """
    Birleşik görme aracı - Ekranı görür, okur ve anlar.
    
    Args:
        task: Görev türü (opsiyonel)
              - None veya "gör": Genel ekran analizi
              - "oku": Tüm metinleri oku (URL/link dahil - yüksek doğruluk)
              - "anla": Detaylı içerik analizi
        
        region: Zoom yapılacak bölge (opsiyonel)
                - "üst", "alt", "sol", "sağ", "merkez"
                - "üst-sol", "üst-sağ", "alt-sol", "alt-sağ"
                - "navbar", "sidebar-sol", "sidebar-sağ", "içerik"
                - Veya tuple: (x1, y1, x2, y2) 0-1 aralığında
        
        find: Bulunacak element adı (opsiyonel)
              - "play butonu", "arama kutusu", "gönder butonu" vb.
    
    Returns:
        Dict with analysis results
    """
    if not GENAI_AVAILABLE:
        return {"error": "Gemini API kullanılamıyor"}
    
    # Get current frame from state
    try:
        from core import state
        if not state.latest_image_payload:
            return {"error": "Ekran görüntüsü yok. 'share_screen' ile ekranı paylaş."}
        
        image_data = state.latest_image_payload.get('data', b'')
        mime_type = state.latest_image_payload.get('mime_type', 'image/jpeg')
        
    except Exception as e:
        return {"error": f"State erişim hatası: {str(e)}"}
    
    # Apply region/zoom if specified
    if region:
        image_data, mime_type = _apply_region(image_data, region)
    
    # Determine prompt based on task (use loaded prompts)
    if find:
        prompt = _PROMPTS["find"].replace("{element}", find)
    elif task in ["oku", "read", "metin"]:
        prompt = _PROMPTS["read"]
    elif task in ["anla", "analyze", "analiz"]:
        prompt = _PROMPTS["general"]
    else:
        prompt = _PROMPTS["general"]
    
    # Call Gemini Vision
    try:
        encoded_image = base64.b64encode(image_data).decode('utf-8')
        
        response = _client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": encoded_image}}
                ]
            }],
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        result = json.loads(response.text)
        
        # Add metadata
        result["_region"] = region if region else "full"
        result["_task"] = task if task else "general"
        
        return result
        
    except json.JSONDecodeError:
        return {"error": "JSON parse hatası", "raw": response.text[:500]}
    except Exception as e:
        return {"error": str(e)}


def _apply_region(image_data: bytes, region) -> Tuple[bytes, str]:
    """
    Görüntüye zoom/crop uygular.
    PNG formatında döndürür (metin için daha iyi kalite).
    """
    try:
        from PIL import Image
        
        # Load image
        img = Image.open(BytesIO(image_data))
        width, height = img.size
        
        # Parse region
        if isinstance(region, str):
            region_lower = region.lower().replace(" ", "-")
            if region_lower in REGIONS:
                x1_pct, y1_pct, x2_pct, y2_pct = REGIONS[region_lower]
            else:
                # Unknown region, return full image
                logger.warning(f"Bilinmeyen bölge: {region}")
                return image_data, "image/jpeg"
        elif isinstance(region, (list, tuple)) and len(region) == 4:
            x1_pct, y1_pct, x2_pct, y2_pct = region
        else:
            return image_data, "image/jpeg"
        
        # Calculate pixel coordinates
        x1 = int(x1_pct * width)
        y1 = int(y1_pct * height)
        x2 = int(x2_pct * width)
        y2 = int(y2_pct * height)
        
        # Crop
        cropped = img.crop((x1, y1, x2, y2))
        
        # Convert to PNG for better text quality
        buffer = BytesIO()
        cropped.save(buffer, format="PNG")
        buffer.seek(0)
        
        logger.info(f"Region applied: {region} -> {cropped.size}")
        
        return buffer.getvalue(), "image/png"
        
    except Exception as e:
        logger.error(f"Region uygulama hatası: {e}")
        return image_data, "image/jpeg"


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================
def read_screen(region: str = None) -> Dict:
    """Ekrandaki metinleri oku (kısayol)"""
    return see_screen(task="oku", region=region)


def find_element(element_name: str) -> Dict:
    """UI elementi bul (kısayol)"""
    return see_screen(find=element_name)


def analyze_screen(region: str = None) -> Dict:
    """Ekranı analiz et (kısayol)"""
    return see_screen(task="anla", region=region)


# ============================================================================
# AVAILABLE REGIONS (for help)
# ============================================================================
def get_available_regions() -> List[str]:
    """Kullanılabilir bölgeleri listele"""
    return list(REGIONS.keys())
