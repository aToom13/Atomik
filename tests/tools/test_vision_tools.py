
import pytest
from unittest.mock import MagicMock
from core.unified_vision import see_screen

def test_see_screen_online(mocker):
    """Test see_screen using Router in Online Mode (Gemini)"""
    # Mock state
    mocker.patch("core.state.latest_image_payload", {"data": b"fake", "mime_type": "image/jpeg"})
    
    # Mock Router
    mock_router = MagicMock()
    mock_router.connection.is_online = True
    
    # Mock Gemini Client inside Router
    mock_response = MagicMock()
    mock_response.text = '{"application": "vscode", "activity": "coding"}'
    
    mock_gemini = MagicMock()
    mock_gemini.models.generate_content.return_value = mock_response
    mock_router.gemini_client = mock_gemini
    
    # Patch the _router in unified_vision
    mocker.patch("core.unified_vision._router", mock_router)
    
    result = see_screen(task="analyze")
    
    assert result["application"] == "vscode"
    assert result["activity"] == "coding"
    # Ensure Gemini was called
    mock_gemini.models.generate_content.assert_called_once()


def test_see_screen_offline(mocker):
    """Test see_screen using Router in Offline Mode (Ollama)"""
    # Mock state with DIFFERENT data to avoid cache hit from previous test
    mocker.patch("core.state.latest_image_payload", {"data": b"fake_offline", "mime_type": "image/jpeg"})
    
    # Mock Router
    mock_router = MagicMock()
    mock_router.connection.is_online = False
    mock_router.connection.is_ollama_ready = True
    
    # Mock Ollama Client inside Router
    # Ollama returns raw string, see_screen tries to parse JSON
    mock_router.ollama.analyze_image.return_value = '{"application": "terminal", "activity": "offline_mode"}'
    
    # Patch the _router in unified_vision
    mocker.patch("core.unified_vision._router", mock_router)
    
    result = see_screen(task="analyze")
    
    assert result["application"] == "terminal"
    assert result["activity"] == "offline_mode"
    # Ensure Ollama was called
    mock_router.ollama.analyze_image.assert_called_once()

def test_see_screen_no_image(mocker):
    """Test error when no image available"""
    mocker.patch("core.state.latest_image_payload", None)
    # We still need to mock router to avoid import errors or checks if any
    mock_router = MagicMock()
    mocker.patch("core.unified_vision._router", mock_router)
    
    result = see_screen()
    assert "error" in result
