
import pytest
from unittest.mock import patch, MagicMock
from tools.llm.router import LLMRouter

class TestLLMRouter:
    def setup_method(self):
        LLMRouter._instance = None
        
    @patch('tools.llm.router.get_connection_manager')
    @patch('tools.llm.router.genai')
    @patch('tools.llm.router.OllamaClient')
    def test_routes_to_gemini_when_online(self, MockOllama, MockGenAI, mock_get_cm):
        """İnternet varken Gemini çağrılmalı"""
        # Setup Connection
        mock_cm = MagicMock()
        mock_cm.is_online = True
        mock_get_cm.return_value = mock_cm
        
        # Setup Gemini
        mock_gemini_instance = MagicMock()
        mock_gemini_instance.models.generate_content.return_value.text = "Gemini Response"
        MockGenAI.Client.return_value = mock_gemini_instance
        
        router = LLMRouter()
        response = router.generate_text("Hi")
        
        assert response == "Gemini Response"
        mock_gemini_instance.models.generate_content.assert_called_once()
        router.ollama.generate_text.assert_not_called()

    @patch('tools.llm.router.get_connection_manager')
    @patch('tools.llm.router.genai')
    @patch('tools.llm.router.OllamaClient')
    def test_routes_to_ollama_when_offline(self, MockOllama, MockGenAI, mock_get_cm):
        """İnternet yokken Ollama çağrılmalı"""
        # Setup Connection
        mock_cm = MagicMock()
        mock_cm.is_online = False
        mock_cm.is_ollama_ready = True
        mock_get_cm.return_value = mock_cm
        
        # Setup Ollama via instance inside router
        # Router init olduğunda self.ollama = OllamaClient() çalışır.
        # MockOllama class mock olduğu için, return_value'su instance olur.
        
        router = LLMRouter()
        # Mock instance'ı router içinden alalım
        mock_ollama_instance = router.ollama
        mock_ollama_instance.generate_text.return_value = "Ollama Response"
        
        response = router.generate_text("Hi")
        
        assert response == "Ollama Response"
        mock_ollama_instance.generate_text.assert_called_once()
        # Gemini çağrılmamalı
        # (Router init'te gemini client oluşur ama generate_text içinde if is_online false olduğu için girmez)
