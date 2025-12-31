"""
LLM Router
Bağlantı durumuna göre Google Gemini veya Yerel Ollama modellerini çağıran yönlendirici katman.
"""
import os
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from AtomBase.config import config
from AtomBase.utils.logger import get_logger
from core.connection import get_connection_manager
from tools.llm.ollama_client import OllamaClient

logger = get_logger()

class LLMRouter:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return
            
        self._initialized = True
        self.connection = get_connection_manager()
        self.ollama = OllamaClient()
        
        # Gemini Init
        self.gemini_client = None
        # Config objesinde API KEY yok, sadece env'den alıyoruz.
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        if GENAI_AVAILABLE and self.api_key:
            try:
                self.gemini_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"Gemini init error: {e}")
        else:
            logger.warning("Google GenAI library or API Key not found. Cloud features disabled.")

    def _get_system_prompt(self, type_key="core", force_offline=False):
        """Offline/Online durumuna göre prompt dosyasını okur"""
        # force_offline veya internet yoksa offline prompt kullan
        if force_offline or not self.connection.is_online:
            try:
                base_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "AtomBase/prompts/offline")
                filename = f"{type_key}_offline.txt"
                with open(os.path.join(base_path, filename), "r") as f:
                    logger.info(f"Loaded offline system prompt: {filename}")
                    return f.read()
            except Exception as e:
                logger.warning(f"Offline prompt read error for {type_key}: {e}")
                return "Sen Atomik'sin - Akif'in yapay zeka asistanı. Türkçe konuş, kısa ve samimi cevaplar ver."
        return None

    def generate_text(self, prompt, system_prompt=None, stream=False, force_offline=False):
        """Metin üretimi için yönlendirme"""
        
        # 1. ONLINE
        if not force_offline and self.connection.is_online and self.gemini_client:
            try:
                # Online çağrı (Gemini 2.0 Flash vb)
                # Not: Caller'ın gönderdiği system_prompt'u kullanırız.
                model_id = "gemini-2.0-flash-exp" 
                
                config_args = types.GenerateContentConfig(
                     system_instruction=system_prompt,
                     temperature=0.7
                )
                
                response = self.gemini_client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                    config=config_args
                )
                return response.text
            except Exception as e:
                logger.error(f"Gemini Error (Falling back to Ollama?): {e}")
                # Hata durumunda offline'a düşülebilir (Fallback)
                pass

        # 2. OFFLINE / FALLBACK
        if self.connection.is_ollama_ready:
            logger.info("Using OLLAMA (Local) for text generation.")
            
            # Offline system prompt'u yükle (Eğer özel bir tane verilmediyse veya override edilecekse)
            # Burada caller'ın gönderdiği system_prompt online için uygun olabilir (çok uzun).
            # Offline için optimize edilmişi çekelim.
            offline_sys = self._get_system_prompt("core", force_offline=True)
            
            return self.ollama.generate_text(prompt, system_prompt=offline_sys, stream=stream)
        
        return "⚠️ Hata: Ne internet var ne de yerel model çalışıyor."

    def analyze_image(self, image_path, prompt, stream=False):
        """Görsel analizi için yönlendirme"""
        
        if self.connection.is_online and self.gemini_client:
            try:
                # Gemini Vision Implementation
                # (Basitleştirilmiş, detaylar unified_vision.py'den taşınabilir)
                # Şimdilik placeholder, çünkü asıl logic unified_vision'da. 
                # Refactoring aşamasında burası dolacak.
                pass 
            except Exception:
                pass
                
        if self.connection.is_ollama_ready:
            logger.info("Using OLLAMA (Local) for vision.")
            return self.ollama.analyze_image(image_path, prompt, stream)
            
        return "⚠️ Vision unavailable."

    def embed_content(self, text):
        """Embedding için yönlendirme"""
        if self.connection.is_online and self.gemini_client:
            try:
                response = self.gemini_client.models.embed_content(
                    model="text-embedding-004",
                    contents=text
                )
                return response.embeddings[0].values
            except Exception as e:
                logger.error(f"Gemini Embed Error: {e}")
        
        if self.connection.is_ollama_ready:
            return self.ollama.embed_content(text)
            
        return []

# Global Accessor
def get_llm_router():
    return LLMRouter.get_instance()
