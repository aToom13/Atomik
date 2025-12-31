import pytest
import time
from core.proactive import ProactiveManager, set_reminder, check_proactive

class TestProactiveManager:
    @pytest.fixture
    def pm(self):
        """Create a fresh manager for each test"""
        return ProactiveManager()

    def test_set_reminder(self, pm):
        """Test setting a reminder"""
        msg = pm.set_reminder(10, "Test reminder")
        assert "Hatırlatıcı kuruldu" in msg
        assert len(pm.reminders) == 1
        assert pm.reminders[0].message == "Test reminder"

    def test_reminder_due(self, pm):
        """Test reminder triggering after time passes"""
        # Set reminder for 1 second
        pm.set_reminder(1, "Due reminder")
        
        # Check immediately (should not be due)
        due = pm.check_reminders()
        assert len(due) == 0
        
        # Wait
        time.sleep(1.1)
        
        # Check again (should be due)
        due = pm.check_reminders()
        assert len(due) == 1
        assert "Due reminder" in due[0]
        
        # Check list empty
        assert len(pm.reminders) == 0

    def test_watcher_lifecycle(self, pm):
        """Test watcher setting and triggering"""
        pm.set_watcher("ekranda hata varsa", "Hata var!")
        
        conditions = pm.get_watcher_conditions()
        assert len(conditions) == 1
        assert "ekranda hata" in conditions[0]
        
        # Trigger it
        result = pm.trigger_watcher(conditions[0])
        assert "Hata var!" in result
        assert "[İZLEYİCİ]" in result
        
        # Should be gone or marked triggered
        active = pm.get_watcher_conditions()
        assert len(active) == 0

    def test_pending_messages(self, pm):
        """Test message queue"""
        pm.add_pending_message("Hello")
        assert pm.has_pending() is True
        
        msgs = pm.get_pending_messages()
        assert len(msgs) == 1
        assert msgs[0] == "Hello"
        assert pm.has_pending() is False
