
import pytest
from unittest.mock import patch, MagicMock, mock_open
from tools.llm.ollama_client import OllamaClient
import requests

class TestOllamaClient:
    
    @patch('requests.post')
    def test_generate_text_success(self, mock_post):
        """Chat fonksiyonu başarılı yanıt dönmeli"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"message": {"content": "Hello from OLLAMA"}}
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        response = client.generate_text("Hi")
        
        assert response == "Hello from OLLAMA"
        # Timeout kontrolü
        assert mock_post.call_args[1]['timeout'] == 30

    @patch('requests.post')
    def test_generate_text_timeout(self, mock_post):
        """Timeout durumunda hata mesajı dönmeli"""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        client = OllamaClient()
        response = client.generate_text("Hi")
        
        assert "Timeout" in response

    @patch('requests.post')
    def test_analyze_image_success(self, mock_post):
        """Vision fonksiyonu başarılı yanıt dönmeli"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "A cat"}
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        with patch("builtins.open", mock_open(read_data=b"image_data")):
            response = client.analyze_image("dummy.jpg")
            
        assert response == "A cat"
        # Vision timeout kontrolü (90s olmalı)
        assert mock_post.call_args[1]['timeout'] == 90

    def test_context_pruning(self):
        """Çok uzun contextler kırpılmalı"""
        client = OllamaClient()
        # 12000 char limiti var
        long_text = "A" * 13000
        pruned = client._prune_context(long_text)
        
        assert len(pruned) < 13000
        assert "[...DIKKAT: METIN OZETLENDI/KIRPILDI...]" in pruned
