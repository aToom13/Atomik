"""
Tests for core/offline module
Offline sistem testleri
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


class TestOfflineTools:
    """OfflineTools sınıfı testleri"""
    
    @pytest.fixture
    def tools(self, tmp_path):
        """Geçici workspace ile OfflineTools oluştur"""
        from core.offline import OfflineTools
        
        # Patch workspace_dir
        tools = OfflineTools()
        tools.workspace_dir = tmp_path / "workspace"
        tools.workspace_dir.mkdir(exist_ok=True)
        tools.notes_dir = tmp_path / "notes"
        tools.notes_dir.mkdir(exist_ok=True)
        return tools
    
    def test_create_file(self, tools):
        """Dosya oluşturma testi"""
        result = tools.create_file("test.txt", "Hello World")
        
        assert "oluşturuldu" in result
        assert (tools.workspace_dir / "test.txt").exists()
        assert (tools.workspace_dir / "test.txt").read_text() == "Hello World"
    
    def test_create_file_empty(self, tools):
        """Boş dosya oluşturma"""
        result = tools.create_file("empty.txt", "")
        
        assert "oluşturuldu" in result
        assert (tools.workspace_dir / "empty.txt").exists()
    
    def test_read_file(self, tools):
        """Dosya okuma testi"""
        # Önce dosya oluştur
        (tools.workspace_dir / "read_test.txt").write_text("Test içerik")
        
        result = tools.read_file("read_test.txt")
        
        assert "Test içerik" in result
    
    def test_read_file_not_found(self, tools):
        """Olmayan dosya okuma"""
        result = tools.read_file("nonexistent.txt")
        
        assert "bulunamadı" in result
    
    def test_list_files(self, tools):
        """Dosya listeleme testi"""
        # Birkaç dosya oluştur
        (tools.workspace_dir / "file1.txt").write_text("1")
        (tools.workspace_dir / "file2.txt").write_text("2")
        
        result = tools.list_files()
        
        assert "file1.txt" in result
        assert "file2.txt" in result
    
    def test_list_files_empty(self, tools):
        """Boş dizin listeleme"""
        result = tools.list_files()
        
        assert "boş" in result
    
    def test_append_to_file(self, tools):
        """Dosyaya ekleme testi"""
        # Önce dosya oluştur
        (tools.workspace_dir / "append_test.txt").write_text("Başlangıç")
        
        result = tools.append_to_file("append_test.txt", "Eklenen metin")
        
        content = (tools.workspace_dir / "append_test.txt").read_text()
        assert "Başlangıç" in content
        assert "Eklenen metin" in content
    
    def test_get_datetime(self, tools):
        """Tarih/saat testi"""
        result = tools.get_datetime()
        
        assert "2025" in result or "2024" in result  # Yıl olmalı


class TestIntentClassifier:
    """IntentClassifier testleri"""
    
    @pytest.fixture
    def classifier(self):
        from core.offline import IntentClassifier
        return IntentClassifier()
    
    def test_tools_defined(self, classifier):
        """Araçların tanımlı olduğunu kontrol et"""
        assert "dosya_olustur" in classifier.TOOLS
        assert "tikla" in classifier.TOOLS
        assert "uygulama_ac" in classifier.TOOLS


class TestGetToolResponse:
    """get_tool_response fonksiyonu testleri"""
    
    @pytest.fixture
    def tools(self, tmp_path):
        from core.offline import OfflineTools
        tools = OfflineTools()
        tools.workspace_dir = tmp_path / "workspace"
        tools.workspace_dir.mkdir(exist_ok=True)
        return tools
    
    def test_file_creation_keywords(self, tools):
        """Dosya oluşturma keyword'lerinin eşleştiğini kontrol et"""
        from core.offline import get_tool_response
        
        test_cases = [
            "yeni bir dosya oluştur",
            "metin belgesi yarat",
            "not kaydet",
        ]
        
        for text in test_cases:
            used, response = get_tool_response(text, tools)
            assert used == True, f"'{text}' için tool kullanılmalıydı"
    
    def test_datetime_request(self, tools):
        """Tarih/saat isteğinin çalıştığını kontrol et"""
        from core.offline import get_tool_response
        
        used, response = get_tool_response("saat kaç", tools)
        
        assert used == True
        assert response is not None
    
    def test_list_files_request(self, tools):
        """Dosya listeleme isteğinin çalıştığını kontrol et"""
        from core.offline import get_tool_response
        
        used, response = get_tool_response("dosyaları listele", tools)
        
        assert used == True


class TestOllamaClient:
    """OllamaClient testleri"""
    
    def test_init(self):
        """Client başlatma testi"""
        from core.offline import OllamaClient
        
        client = OllamaClient()
        
        assert client.base_url == "http://localhost:11434"
        assert client.model_chat is not None
    
    def test_context_pruning(self):
        """Context kırpma testi"""
        from core.offline import OllamaClient
        
        client = OllamaClient()
        
        # Kısa metin değiştirilmemeli
        short_text = "Kısa metin"
        assert client._prune_context(short_text) == short_text
        
        # Uzun metin kırpılmalı
        long_text = "A" * 20000
        pruned = client._prune_context(long_text)
        assert len(pruned) < len(long_text)
        assert "KIRPILDI" in pruned or len(pruned) <= client.max_context_chars + 100
