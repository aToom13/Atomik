
import pytest
from unittest.mock import patch, MagicMock
from core.connection import ConnectionManager

class TestConnectionManager:
    def setup_method(self):
        # Singleton instance'ı resetle
        ConnectionManager._instance = None
    
    @patch('requests.get')
    @patch('socket.socket')
    def test_internet_check_success(self, mock_socket, mock_requests):
        """İnternet varken True dönmeli"""
        # Requests mock setup (Ollama check için gerekli)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests.return_value = mock_response
        
        cm = ConnectionManager()
        # socket.connect hata vermezse internet var demektir
        assert cm.is_online is True

    @patch('requests.get')
    @patch('socket.socket')
    def test_internet_check_failure(self, mock_socket, mock_requests):
        """Socket hatasında False dönmeli"""
        # Requests mock setup
        mock_requests.return_value = MagicMock(status_code=200)

        # connect metodu hata fırlatsın
        mock_socket_instance = MagicMock()
        mock_socket_instance.connect.side_effect = OSError("Network is unreachable")
        mock_socket.return_value = mock_socket_instance
        
        cm = ConnectionManager()
        assert cm.is_online is False

    @patch('requests.get')
    def test_ollama_check_success(self, mock_get):
        """Ollama çalışıyorsa True dönmeli"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        cm = ConnectionManager()
        assert cm.is_ollama_ready is True

    @patch('requests.get')
    def test_ollama_check_failure(self, mock_get):
        """Ollama hatasında False dönmeli"""
        # requests hata fırlatsın
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        cm = ConnectionManager()
        # İlk init'te check_ollama çağrılır, mock hatası yakalanır -> False olur
        assert cm.is_ollama_ready is False
