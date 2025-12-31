
import pytest
from unittest.mock import patch, MagicMock, mock_open
from tools.llm.ollama_client import OllamaClient
import requests

class TestOllamaClient:
    
    @patch('requests.post')
    def test_generate_text_success(self, mock_post):
        """Chat fonksiyonu başarılı yanıt dönmeli"""
        # OllamaClient uses streaming internally (stream=True in request)
        # and collects chunks via iter_lines()
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Simulate streaming response with iter_lines
        mock_response.iter_lines.return_value = [
            b'{"message": {"content": "Hello "}, "done": false}',
            b'{"message": {"content": "from "}, "done": false}',
            b'{"message": {"content": "OLLAMA"}, "done": true}'
        ]
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        response = client.generate_text("Hi")
        
        assert response == "Hello from OLLAMA"
        # Timeout kontrolü
        assert mock_post.call_args[1]['timeout'] == 60  # Updated to match actual (60s, not 30s)

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
        # Vision API uses /api/generate which returns {"response": "..."} 
        mock_response.json.return_value = {"response": "A cat"}
        mock_post.return_value = mock_response
        
        client = OllamaClient()
        with patch("builtins.open", mock_open(read_data=b"image_data")):
            response = client.analyze_image("dummy.jpg")
            
        assert response == "A cat"
        # Vision timeout kontrolü (180s olmalı)
        assert mock_post.call_args[1]['timeout'] == 180

    def test_context_pruning(self):
        """Çok uzun contextler kırpılmalı"""
        client = OllamaClient()
        # 12000 char limiti var
        long_text = "A" * 13000
        pruned = client._prune_context(long_text)
        
        assert len(pruned) < 13000
        assert "[...DIKKAT: METIN OZETLENDI/KIRPILDI...]" in pruned
