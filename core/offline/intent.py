"""
Atomik Intent Classifier - LLM-based tool routing
Uses local Ollama to classify user intent and extract parameters.
"""

import json
import logging
import re
from typing import Optional, Dict, Tuple

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    LLM tabanlı niyet sınıflandırıcı.
    Kullanıcının ne istediğini anlar ve uygun aracı belirler.
    """
    
    # Desteklenen araçlar ve açıklamaları
    TOOLS = {
        "dosya_olustur": "Yeni dosya oluştur (metin belgesi, not, kod dosyası vb.)",
        "dosya_oku": "Mevcut dosyayı oku/göster",
        "dosya_duzenle": "Mevcut dosyayı düzenle/değiştir",
        "dosya_ekle": "Mevcut dosyaya içerik ekle",
        "dosya_listele": "Dosyaları listele",
        "uygulama_ac": "Uygulama aç (terminal, tarayıcı vb.)",
        "tikla": "Ekranda bir elemente tıkla",
        "yaz": "Metin yaz/gir (klavye ile)",
        "hotkey": "Klavye kısayolu uygula",
        "hatirlatici": "Hatırlatıcı ekle/listele",
        "tarih_saat": "Tarih ve saat bilgisi",
        "sistem_bilgisi": "Sistem bilgisi göster",
        "sohbet": "Genel sohbet/soru (araç gerektirmez)"
    }
    
    def __init__(self):
        self._client = None
    
    def _get_client(self):
        """Lazy load Ollama client"""
        if self._client is None:
            try:
                from core.offline.llm_client import OllamaClient
                self._client = OllamaClient()
            except ImportError:
                logger.warning("OllamaClient not available")
                return None
        return self._client
    
    def classify(self, user_text: str) -> Dict:
        """
        Kullanıcı metnini sınıflandır.
        
        Returns:
            {
                "tool": "dosya_olustur",  # veya None (sohbet için)
                "params": {
                    "filename": "rapor.txt",
                    "content": "...",
                    "topic": "..."
                },
                "confidence": 0.9
            }
        """
        client = self._get_client()
        if not client:
            return {"tool": None, "params": {}, "confidence": 0}
        
        # Build classification prompt
        tools_desc = "\n".join([f"- {k}: {v}" for k, v in self.TOOLS.items()])
        
        prompt = f"""Aşağıdaki kullanıcı komutunu analiz et ve hangi aracın kullanılacağını belirle.

ÖNEMLİ KURALLAR:
- "yap", "oluştur", "yaz", "kodla" gibi kelimeler genellikle dosya_olustur demek
- "tıkla", "bas" açıkça söylenmeden tikla seçme
- Kod/program/oyun istekleri = dosya_olustur (kod dosyası)
- Sadece ekrandaki bir şeye tıklama isteniyorsa tikla

ARAÇLAR:
{tools_desc}

ÖRNEKLER:
- "Flappy Bird oyunu yap" → dosya_olustur (Python oyunu)
- "Accept butonuna tıkla" → tikla
- "Terminal aç" → uygulama_ac
- "Bir hikaye yaz" → dosya_olustur (metin dosyası)
- "Mavi butona bas" → tikla

KULLANICI KOMUTU: "{user_text}"

Yanıtını şu JSON formatında ver (sadece JSON, başka hiçbir şey yazma):
{{
    "tool": "araç_adı_veya_null",
    "params": {{
        "filename": "dosya adı (varsa)",
        "content": "içerik (varsa)", 
        "topic": "konu/açıklama (varsa)",
        "target": "hedef element/uygulama (varsa)",
        "position": "konum ipucu (varsa)",
        "color": "renk (varsa)"
    }},
    "reason": "kısa açıklama"
}}
"""
        
        try:
            response = client.generate_text(prompt)
            
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group(0))
                
                # Clean empty params
                if "params" in result:
                    result["params"] = {k: v for k, v in result["params"].items() if v and v != "null"}
                
                return result
            else:
                logger.warning(f"Could not extract JSON from LLM response: {response}")
                return {"tool": None, "params": {}, "confidence": 0}
                
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return {"tool": None, "params": {}, "confidence": 0}
        except Exception as e:
            logger.error(f"Intent classification error: {e}")
            return {"tool": None, "params": {}, "confidence": 0}


# Global instance
_classifier: Optional[IntentClassifier] = None

def get_intent_classifier() -> IntentClassifier:
    """Get or create global intent classifier"""
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier


def classify_intent(user_text: str) -> Dict:
    """Convenience function for intent classification"""
    return get_intent_classifier().classify(user_text)
