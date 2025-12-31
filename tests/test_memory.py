import pytest
import time
from tools.memory.unified_memory import WorkingMemory, EpisodicMemory, SemanticMemory

class TestWorkingMemory:
    @pytest.fixture
    def wm(self):
        """Create a WorkingMemory with short TTL for testing"""
        return WorkingMemory(max_items=10, ttl_seconds=2)
        
    def test_add_and_get(self, wm):
        """Test adding and retrieving items"""
        wm.add({"type": "test", "content": "hello"})
        recent = wm.get_recent(1)
        assert len(recent) == 1
        assert recent[0]["content"] == "hello"
        
    def test_ttl_expiration(self, wm):
        """Test that items expire after TTL"""
        wm.add({"content": "old"})
        time.sleep(2.1)
        wm.add({"content": "new"})
        
        recent = wm.get_recent()
        assert len(recent) == 1
        assert recent[0]["content"] == "new"

    def test_search(self, wm):
        """Test simple search capability"""
        wm.add({"content": "apple pie"})
        wm.add({"content": "banana bread"})
        
        results = wm.search("apple")
        assert len(results) == 1
        assert results[0]["content"] == "apple pie"

class TestSemanticMemory:
    @pytest.fixture
    def sm(self, tmp_path):
        """Create a SemanticMemory with a temp file"""
        # Use a temporary file path
        f = tmp_path / "semantic.json"
        return SemanticMemory(filepath=str(f))

    def test_update_recursive(self, sm):
        """Test nested updates"""
        sm.update("user.profile.name", "Atom")
        assert sm.get("user.profile.name") == "Atom"
        
        sm.update("user.preferences.color", "Blue")
        assert sm.get("user.preferences.color") == "Blue"
        # Check if previous data preserved
        assert sm.get("user.profile.name") == "Atom"

    def test_delete(self, sm):
        """Test deletion"""
        sm.update("a.b", 1)
        sm.delete("a.b")
        assert sm.get("a.b") is None
        assert sm.get("a") == {}

class TestEpisodicMemory:
    @pytest.fixture
    def em(self, tmp_path, mocker):
        """Create EpisodicMemory with forced fallback mode for testing"""
        # Mock chromadb import to force fallback mode
        mocker.patch.dict('sys.modules', {'chromadb': None})
        
        # Also mock sentence_transformers to be safe
        mocker.patch.dict('sys.modules', {'sentence_transformers': None})
        
        from tools.memory.unified_memory import EpisodicMemory
        em = EpisodicMemory()
        # Ensure fallback mode (no ChromaDB)
        em.use_chroma = False
        em._fallback_episodes = []
        return em

    def test_save_episode(self, em):
        """Test saving without error"""
        # save_episode returns message when importance >= 0.3
        result = em.save_episode("Test episode", {"type": "test"}, importance=0.5)
        # Should return success message
        assert result is not None and "kaydedildi" in result.lower(), f"Unexpected result: {result}"

    def test_fallback_search(self, em):
        """Test fallback search when chroma is mocked/empty"""
        # Force fallback behavior (already set in fixture)
        em._save_to_fallback("Test memory", {"date": "2024-01-01"})
        
        results = em._search_fallback("Test")
        assert len(results) > 0
        assert "Test memory" in results[0]["content"]
