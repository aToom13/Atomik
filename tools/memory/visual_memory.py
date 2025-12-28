"""
Visual Memory - Görsel gözlemleri kaydet ve karşılaştır
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

MEMORY_DIR = Path(__file__).parent.parent / ".memory"
VISUAL_FILE = MEMORY_DIR / "visual_observations.json"

def _ensure_dir():
    MEMORY_DIR.mkdir(exist_ok=True)

def _load_observations() -> List[Dict]:
    """Load visual observations from file"""
    _ensure_dir()
    if VISUAL_FILE.exists():
        try:
            with open(VISUAL_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def _save_observations(observations: List[Dict]):
    """Save visual observations to file"""
    _ensure_dir()
    # Keep only last 20 observations
    observations = observations[-20:]
    with open(VISUAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(observations, f, ensure_ascii=False, indent=2)

def save_visual_observation(notes: str, attributes: Optional[Dict] = None) -> str:
    """
    Oturum sonunda görsel gözlem kaydet
    
    Args:
        notes: Genel gözlem notları (örn: "Gözlüklü, beyaz tişört")
        attributes: Yapılandırılmış özellikler (örn: {"glasses": true, "hair": "kısa"})
    
    Returns:
        Onay mesajı
    """
    observations = _load_observations()
    
    observation = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "notes": notes,
        "attributes": attributes or {}
    }
    
    observations.append(observation)
    _save_observations(observations)
    
    return f"✅ Görsel gözlem kaydedildi: {notes}"

def get_last_observation() -> Optional[Dict]:
    """Son görsel gözlemi getir"""
    observations = _load_observations()
    if observations:
        return observations[-1]
    return None

def get_visual_history(count: int = 5) -> str:
    """
    Son N görsel gözlemi getir
    
    Args:
        count: Kaç gözlem getirilsin
    
    Returns:
        Gözlem geçmişi özeti
    """
    observations = _load_observations()
    
    if not observations:
        return "Henüz görsel gözlem yok."
    
    recent = observations[-count:]
    result = "📷 Son Görsel Gözlemler:\n"
    
    for obs in reversed(recent):
        result += f"• {obs['date']}: {obs['notes']}\n"
    
    return result.strip()

def compare_with_last(current_notes: str) -> str:
    """
    Mevcut görünümü son gözlemle karşılaştır
    
    Args:
        current_notes: Şu anki görünüm notları
    
    Returns:
        Karşılaştırma sonucu
    """
    last = get_last_observation()
    
    if not last:
        return "İlk görüşmemiz! Karşılaştırma yapılamadı."
    
    last_notes = last.get("notes", "")
    last_date = last.get("date", "bilinmiyor")
    
    result = f"📊 Karşılaştırma:\n"
    result += f"Son görüşme ({last_date}): {last_notes}\n"
    result += f"Şimdi: {current_notes}"
    
    return result

def get_visual_context_for_prompt() -> str:
    """Sistem promptu için görsel bağlam hazırla"""
    last = get_last_observation()
    
    if not last:
        return ""
    
    last_date = last.get("date", "")
    last_notes = last.get("notes", "")
    
    return f"[Son görsel gözlem ({last_date}): {last_notes}]"
