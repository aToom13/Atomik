"""
Connection Manager
Sistemin internet ve yerel servis durumlarını kontrol eder.
"""
import os
import socket
import requests
import time
from threading import Thread, Event
from core.colors import Colors
try:
    from AtomBase.utils.logger import get_logger
    logger = get_logger()
except ImportError:
    import logging
    logger = logging.getLogger("ConnectionManager")

class ConnectionManager:
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
        self._is_online = True
        self._is_ollama_available = False
        self._monitor_thread = None
        self._stop_event = Event()
        self._check_interval = 30  # Saniye
        
        # İlk kontrolü hemen yap
        self.check_status()
    
    def start_monitoring(self):
        """Arka planda bağlantı kontrolünü başlat"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        self._stop_event.clear()
        self._monitor_thread = Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("📡 Connection monitoring started.")

    def stop_monitoring(self):
        """İzlemeyi durdur"""
        if self._monitor_thread:
            self._stop_event.set()
            self._monitor_thread.join(timeout=2)
            logger.info("Connection monitoring stopped.")

    def _monitor_loop(self):
        """Periyodik kontrol döngüsü"""
        while not self._stop_event.is_set():
            self.check_status()
            time.sleep(self._check_interval)

    def check_status(self):
        """Anlık durum kontrolü"""
        # 1. İnternet Kontrolü
        prev_online = self._is_online
        self._is_online = self._check_internet()
        
        if prev_online != self._is_online:
            status = "ONLINE 🟢" if self._is_online else "OFFLINE 🔴"
            logger.info(f"Connection status changed: {status}")

        # 2. Ollama Kontrolü
        prev_ollama = self._is_ollama_available
        self._is_ollama_available = self._check_ollama()
        
        if prev_ollama != self._is_ollama_available:
            status = "AVAILABLE 🟢" if self._is_ollama_available else "UNAVAILABLE 🔴"
            logger.info(f"Ollama status changed: {status}")

    def _check_internet(self, host="8.8.8.8", port=53, timeout=3):
        """DNS ping ile internet kontrolü"""
        try:
            socket.setdefaulttimeout(timeout)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect((host, port))
                return True
            finally:
                s.close()
        except socket.error:
            return False

    def _check_ollama(self, url="http://localhost:11434"):
        """Ollama servisi çalışıyor mu?"""
        try:
            response = requests.get(f"{url}/api/tags", timeout=2) # Hızlı cevap için timeout kısa
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    @property
    def is_online(self) -> bool:
        return self._is_online

    @property
    def is_ollama_ready(self) -> bool:
        return self._is_ollama_available

# Global instance helper
def get_connection_manager():
    return ConnectionManager.get_instance()
