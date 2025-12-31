"""
Ollama Client
Yerel LLM (Ollama) ile iletişim kurar.
"""
import requests
import json
import base64
import time
try:
    from AtomBase.utils.logger import get_logger
    logger = get_logger()
except ImportError:
    import logging
    logger = logging.getLogger("OllamaClient")

class OllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        # Modeller
        self.model_chat = "gemma3:4b"  # User installed model
        self.model_vision = "gemma3:4b" # User insists on this
        self.model_embedding = "nomic-embed-text"
        
        # Konfigürasyon (Kullanıcı isteği: Timeout artırıldı)
        self.timeout_chat = 60  # Faster model needs less timeout
        self.timeout_vision = 180  # Vision için daha uzun süre
        self.timeout_embed = 15
        
        # Context Yönetimi (Kullanıcı isteği: Context özeti)
        self.max_context_chars = 12000 # Yaklaşık 3-4k token. Fazlasını kırpacağız.

    def generate_text(self, prompt, system_prompt=None, stream=False):
        """Metin üretimi (Chat completion)"""
        url = f"{self.base_url}/api/chat"
        
        # Context yönetimi
        final_prompt = self._prune_context(prompt)
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        messages.append({"role": "user", "content": final_prompt})

        payload = {
            "model": self.model_chat,
            "messages": messages,
            "stream": True,  # Enable streaming for real-time output
            "think": False,   # Enable thinking mode
            "options": {
                "num_ctx": 4096,
                "temperature": 0.7
            }
        }

        try:
            response = requests.post(url, json=payload, timeout=self.timeout_chat, stream=True)
            response.raise_for_status()
            
            if stream:
                return self._stream_generator(response)
            
            content_buffer = ""
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        message = chunk.get("message", {})
                        
                        # Only collect content (skip thinking)
                        content_token = message.get("content", "")
                        if content_token:
                            content_buffer += content_token
                            
                        # Check if done
                        if chunk.get("done", False):
                            break
                            
                    except json.JSONDecodeError:
                        continue
            
            return content_buffer
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Ollama Chat Timeout ({self.timeout_chat}s)")
            return "⚠️ Hata: Yerel model yanıt vermede gecikti (Timeout)."
        except Exception as e:
            logger.error(f"❌ Ollama Chat Error: {e}")
            return f"⚠️ Hata: {str(e)}"

    def _stream_generator(self, response):
        """Yield chunks from response"""
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                except:
                    continue

    def analyze_image(self, image_path=None, image_bytes=None, prompt="Describe this image", stream=False):
        """Görsel analizi"""
        url = f"{self.base_url}/api/generate" # Vision modelleri genelde generate endpointini kullanır (multimodal)
        
        img_base64 = ""
        try:
            if image_bytes:
                img_base64 = base64.b64encode(image_bytes).decode('utf-8')
            elif image_path:
                with open(image_path, "rb") as img_file:
                    img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            else:
                return "⚠️ Hata: Görüntü verisi yok (path veya bytes gerekli)."
        except Exception as e:
            return f"⚠️ Resim okuma hatası: {e}"

        payload = {
            "model": self.model_vision,
            "prompt": prompt + " /no_think",  # Disable thinking mode
            "images": [img_base64],
            "stream": False,
            "think": False,  # Disable thinking for faster response
            "options": {
                "temperature": 0.2,  # Vision için daha deterministik
                "num_ctx": 2048  # Smaller context for speed
            }
        }

        try:
            # Vision işlemi uzun sürebilir
            response = requests.post(url, json=payload, timeout=self.timeout_vision)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.Timeout:
             logger.error(f"⏱️ Ollama Vision Timeout ({self.timeout_vision}s)")
             return "⚠️ Hata: Görsel analizi zaman aşımına uğradı."
        except Exception as e:
            logger.error(f"❌ Ollama Vision Error: {e}")
            return f"⚠️ Hata: {str(e)}"

    def embed_content(self, text):
        """Metin vektörleştirme (Embedding)"""
        url = f"{self.base_url}/api/embeddings"
        
        payload = {
            "model": self.model_embedding,
            "prompt": text
        }
        
        try:
            response = requests.post(url, json=payload, timeout=self.timeout_embed)
            response.raise_for_status()
            result = response.json()
            return result.get("embedding", [])
        except Exception as e:
            logger.error(f"❌ Ollama Embedding Error: {e}")
            return []

    def _prune_context(self, text):
        """
        Kullanıcı isteği: Context'in özetlenmesi/kırpılması.
        Çok uzun metinleri yerel modelin kaldırabileceği seviyeye indirir.
        Ortadan kırpma stratejisi (Middle Truncation) uygularız, 
        çünkü başı (instruction) ve sonu (son soru) genelde en önemlisidir.
        """
        if len(text) <= self.max_context_chars:
            return text
            
        logger.warning(f"✂️ Context too long ({len(text)} chars). Pruning to {self.max_context_chars}.")
        
        keep_len = self.max_context_chars // 2
        head = text[:keep_len]
        tail = text[-keep_len:]
        
        return f"{head}\n\n[...DIKKAT: METIN OZETLENDI/KIRPILDI...]\n\n{tail}"
