"""
Humanized Error Handler & Logging System
=========================================
Hataları insanca mesajlara çevirir.
Teknik detayları log'a yazar, kullanıcıya samimi mesaj verir.
"""
import os
import sys
import time
import json
import random
import logging
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import Counter

# Project root
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(_project_root, "logs")
os.makedirs(LOG_DIR, exist_ok=True)


# =============================================================================
# HUMANIZED ERROR HANDLER
# =============================================================================
class HumanizedErrorHandler:
    """
    Hataları yakalar ve insanca mesajlara çevirir.
    Kullanıcı teknik jargon görmez, samimi bir açıklama alır.
    """
    
    # Hata türlerine göre insanca mesaj havuzu
    ERROR_MESSAGES: Dict[str, List[str]] = {
        # API Hataları
        "api_timeout": [
            "Şey, bağlantı koptu sanırım. Hemen düzeltiyorum...",
            "Aa, internet mi gitti? Bir saniye...",
            "Hmm, sunucuyla aram bozuldu. Tekrar bağlanıyorum..."
        ],
        "rate_limit": [
            "Biraz yavaşlamamız lazım, çok hızlı gidiyoruz haha",
            "API limiti geldi, 10 saniye mola veriyorum",
            "Çok istek atmışız, biraz bekleyelim"
        ],
        
        # Tool Hataları
        "tool_failed": [
            "O işlemi yapamadım, başka yoldan deniyorum...",
            "Hmm, bu işe yaramadı. Plan B'ye geçiyorum",
            "Şey, bu tool çalışmadı. Alternatif kullanıyorum"
        ],
        "file_not_found": [
            "O dosyayı bulamadım. Başka yerde mi acaba?",
            "Hmm, dosya kaybolmuş galiba. Nerede olmalı?",
            "O dosya yok gibi... Yanlış yer mi?"
        ],
        "permission_denied": [
            "O işlem için iznim yok gibi görünüyor",
            "Erişim engellendi, farklı bir yol deneyelim",
            "İzin hatası aldım, başka çözüm arıyorum"
        ],
        
        # Vision Hataları
        "camera_error": [
            "Kamera bağlantısı koptu. Düzeltiyorum...",
            "Seni göremiyorum şu an, kamera sorun çıkardı",
            "Kamera dondu sanırım, yeniliyorum"
        ],
        "vision_model_error": [
            "Görüntü işleme modeli hata verdi, tekrar deniyorum",
            "Görsel analiz şu an çalışmıyor, bir dakika...",
            "Vision sistemi takıldı, yeniden başlatıyorum"
        ],
        
        # Gemini Live Hataları
        "session_expired": [
            "Ufak bir teknik aksaklık, hemen düzeltiyorum",
            "Bağlantı yenileniyor, 2 saniye...",
            "Sistemde küçük bir takılma oldu, düzelttim"
        ],
        "websocket_error": [
            "Bağlantıda anlık bir kesinti oldu, yeniliyorum",
            "WebSocket kapandı, tekrar bağlanıyorum...",
            "Canlı bağlantı koptu, hemen düzeltiyorum"
        ],
        
        # Memory Hataları
        "memory_error": [
            "Hafızamda bir takılma oldu, tekrar deniyorum",
            "Anıları getirirken sorun yaşadım",
            "Hatırlama sistemi takıldı, düzeltiyorum"
        ],
        
        # Genel / Bilinmeyen
        "unknown": [
            "Beklenmedik bir şey oldu, ama hallediyorum...",
            "Hmm, garip bir hata. Çözüyorum...",
            "Bir aksilik oldu, endişelenme düzeltiyorum"
        ]
    }
    
    # Hata sınıflandırma kuralları
    ERROR_PATTERNS: Dict[str, List[str]] = {
        "api_timeout": ["timeout", "connection", "timed out", "connect", "unreachable"],
        "rate_limit": ["rate", "limit", "quota", "429", "too many"],
        "file_not_found": ["not found", "no such file", "doesn't exist", "does not exist"],
        "permission_denied": ["permission", "denied", "access", "forbidden", "403"],
        "camera_error": ["camera", "video", "webcam", "cv2", "capture"],
        "vision_model_error": ["vision", "image", "analyze", "404"],
        "session_expired": ["session", "expired", "1008", "policy"],
        "websocket_error": ["websocket", "socket", "closed", "1011"],
        "memory_error": ["memory", "chroma", "embedding", "recall"],
        "tool_failed": ["tool", "execute", "failed", "error"]
    }
    
    def __init__(self):
        self.logger = logging.getLogger("atomik.errors")
        self._setup_logging()
        
        # Metrik takibi
        self.error_counts = Counter()
        self.last_errors: List[Dict] = []
    
    def _setup_logging(self):
        """Error log dosyasını ayarla"""
        handler = logging.FileHandler(
            os.path.join(LOG_DIR, "errors.log"),
            encoding='utf-8'
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.ERROR)
    
    def handle(self, error: Exception, context: str = "") -> str:
        """
        Hatayı yakala, insanca mesaj döndür
        
        Args:
            error: Yakalanan exception
            context: Hatanın oluştuğu bağlam (örn: "tool_call", "vision")
            
        Returns:
            Kullanıcıya gösterilecek insanca mesaj
        """
        error_type = self._classify_error(error)
        
        # Metrik kaydet
        self.error_counts[error_type] += 1
        self._record_error(error, error_type, context)
        
        # Teknik detayları log'a yaz
        self._log_technical(error, error_type, context)
        
        # İnsanca mesaj seç
        messages = self.ERROR_MESSAGES.get(error_type, self.ERROR_MESSAGES["unknown"])
        return random.choice(messages)
    
    def _classify_error(self, error: Exception) -> str:
        """
        Hata türünü belirle
        """
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()
        combined = f"{error_str} {error_type_name}"
        
        for error_type, patterns in self.ERROR_PATTERNS.items():
            if any(pattern in combined for pattern in patterns):
                return error_type
        
        return "unknown"
    
    def _log_technical(self, error: Exception, error_type: str, context: str):
        """
        Teknik detayları log dosyasına yaz
        """
        self.logger.error(
            f"[{error_type}] [{context}] {type(error).__name__}: {error}\n"
            f"{traceback.format_exc()}"
        )
    
    def _record_error(self, error: Exception, error_type: str, context: str):
        """
        Hata kaydını tut (debugging için)
        """
        record = {
            "timestamp": time.time(),
            "type": error_type,
            "context": context,
            "message": str(error),
            "class": type(error).__name__
        }
        self.last_errors.append(record)
        
        # Son 50 hatayı tut
        if len(self.last_errors) > 50:
            self.last_errors = self.last_errors[-50:]
    
    def get_error_stats(self) -> Dict:
        """
        Hata istatistiklerini döndür (debugging)
        """
        return {
            "counts": dict(self.error_counts),
            "total": sum(self.error_counts.values()),
            "last_5": self.last_errors[-5:]
        }
    
    def should_retry(self, error: Exception) -> bool:
        """
        Bu hata için retry yapılmalı mı?
        """
        error_type = self._classify_error(error)
        
        # Retry yapılabilir hatalar
        retryable = [
            "api_timeout",
            "rate_limit",
            "session_expired",
            "websocket_error",
            "memory_error"
        ]
        
        return error_type in retryable


# =============================================================================
# ATOMIK LOGGER (Metrics & Performance)
# =============================================================================
class AtomikLogger:
    """
    Kapsamlı logging ve metrik sistemi.
    Tool kullanımı, yanıt süreleri, hatalar takip edilir.
    """
    
    def __init__(self):
        self._setup_loggers()
        
        # Metrikler
        self.metrics = {
            "tool_calls": Counter(),
            "tool_success": Counter(),
            "tool_failures": Counter(),
            "response_times": [],
            "session_start": time.time(),
            "errors": Counter()
        }
    
    def _setup_loggers(self):
        """3 ayrı logger kur"""
        # 1. Genel log
        self.general = logging.getLogger("atomik.general")
        gen_handler = logging.FileHandler(
            os.path.join(LOG_DIR, "atomik.log"),
            encoding='utf-8'
        )
        gen_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s'
        ))
        self.general.addHandler(gen_handler)
        self.general.setLevel(logging.INFO)
        
        # 2. Metrik log (JSONL format)
        self.metrics_logger = logging.getLogger("atomik.metrics")
        metrics_handler = logging.FileHandler(
            os.path.join(LOG_DIR, "metrics.jsonl"),
            encoding='utf-8'
        )
        metrics_handler.setFormatter(logging.Formatter('%(message)s'))
        self.metrics_logger.addHandler(metrics_handler)
        self.metrics_logger.setLevel(logging.INFO)
    
    def log_tool_call(
        self,
        tool_name: str,
        duration: float,
        success: bool,
        result_preview: str = ""
    ):
        """
        Tool kullanımını kaydet
        """
        self.metrics["tool_calls"][tool_name] += 1
        self.metrics["response_times"].append(duration)
        
        if success:
            self.metrics["tool_success"][tool_name] += 1
        else:
            self.metrics["tool_failures"][tool_name] += 1
        
        # JSONL log
        self.metrics_logger.info(json.dumps({
            "type": "tool_call",
            "tool": tool_name,
            "duration": round(duration, 3),
            "success": success,
            "result_preview": result_preview[:100] if result_preview else "",
            "timestamp": time.time()
        }, ensure_ascii=False))
        
        # Genel log
        status = "✓" if success else "✗"
        self.general.info(f"[TOOL] {status} {tool_name} ({duration:.2f}s)")
    
    def log_conversation(self, role: str, content: str):
        """
        Konuşma kaydı
        """
        self.general.info(f"[{role.upper()}] {content[:200]}")
        
        self.metrics_logger.info(json.dumps({
            "type": "conversation",
            "role": role,
            "content_length": len(content),
            "timestamp": time.time()
        }))
    
    def log_event(self, event_type: str, details: Dict = None):
        """
        Özel olay kaydı
        """
        self.general.info(f"[EVENT] {event_type}: {details}")
        
        self.metrics_logger.info(json.dumps({
            "type": "event",
            "event": event_type,
            "details": details or {},
            "timestamp": time.time()
        }, ensure_ascii=False))
    
    def get_daily_report(self) -> str:
        """
        Günlük performans raporu oluştur
        """
        uptime = time.time() - self.metrics["session_start"]
        uptime_hours = uptime / 3600
        
        avg_response = 0
        if self.metrics["response_times"]:
            avg_response = sum(self.metrics["response_times"]) / len(self.metrics["response_times"])
        
        total_calls = sum(self.metrics["tool_calls"].values())
        total_success = sum(self.metrics["tool_success"].values())
        success_rate = (total_success / total_calls * 100) if total_calls > 0 else 0
        
        # En çok kullanılan tool'lar
        top_tools = self.metrics["tool_calls"].most_common(5)
        top_tools_str = "\n".join([f"  - {t}: {c} kez" for t, c in top_tools])
        
        report = f"""
📊 ATOMIK GÜNLÜK PERFORMANS RAPORU
{'='*40}
⏱️ Çalışma Süresi: {uptime_hours:.1f} saat

🛠️ Tool Kullanımı:
{top_tools_str}

📈 İstatistikler:
  - Toplam çağrı: {total_calls}
  - Başarı oranı: {success_rate:.1f}%
  - Ort. yanıt süresi: {avg_response:.2f}s

❌ Hatalar:
{dict(self.metrics["errors"]) if self.metrics["errors"] else "  Hata yok! 🎉"}
"""
        return report.strip()
    
    def reset_metrics(self):
        """
        Metrikleri sıfırla (yeni gün için)
        """
        self.metrics = {
            "tool_calls": Counter(),
            "tool_success": Counter(),
            "tool_failures": Counter(),
            "response_times": [],
            "session_start": time.time(),
            "errors": Counter()
        }


# =============================================================================
# GLOBAL INSTANCES
# =============================================================================
error_handler: Optional[HumanizedErrorHandler] = None
atomik_logger: Optional[AtomikLogger] = None


def get_error_handler() -> HumanizedErrorHandler:
    """Global error handler instance"""
    global error_handler
    if error_handler is None:
        error_handler = HumanizedErrorHandler()
    return error_handler


def get_atomik_logger() -> AtomikLogger:
    """Global logger instance"""
    global atomik_logger
    if atomik_logger is None:
        atomik_logger = AtomikLogger()
    return atomik_logger
