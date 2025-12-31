import os
import sys
import pytest
from unittest.mock import MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set environment variables for testing"""
    monkeypatch.setenv("GOOGLE_API_KEY", "test_key_12345")
    monkeypatch.setenv("GEMINI_API_KEY", "test_key_12345")
    monkeypatch.setenv("TEST_MODE", "true")

@pytest.fixture
def mock_genai_client(mocker):
    """Mock Google GenAI Client to prevent real API calls"""
    mock_client = MagicMock()
    mocker.patch("google.genai.Client", return_value=mock_client)
    mocker.patch("tools.memory.rag_memory.genai", MagicMock())
    mocker.patch("core.unified_vision.genai", MagicMock())
    return mock_client

@pytest.fixture
def mock_chromadb(mocker):
    """Mock ChromaDB to prevent disk usage"""
    mock_db = MagicMock()
    mocker.patch("chromadb.PersistentClient", return_value=mock_db)
    mocker.patch("tools.memory.rag_memory.chromadb", MagicMock())
    return mock_db

@pytest.fixture
def mock_pyaudio(mocker):
    """Mock PyAudio to prevent audio device errors"""
    mock_pa = MagicMock()
    mocker.patch("pyaudio.PyAudio", return_value=mock_pa)
    return mock_pa
