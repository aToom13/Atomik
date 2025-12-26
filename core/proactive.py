"""
Proactive Assistant System
- Reminders: Set time-based reminders
- Watchers: Watch for conditions on screen/camera
"""
import asyncio
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class Reminder:
    """A time-based reminder"""
    trigger_time: float  # Unix timestamp when to trigger
    message: str
    created_at: float = field(default_factory=time.time)
    
    def is_due(self) -> bool:
        return time.time() >= self.trigger_time
    
    def time_remaining(self) -> float:
        return max(0, self.trigger_time - time.time())

@dataclass  
class Watcher:
    """A condition-based watcher for screen/camera"""
    condition: str  # Description of what to watch for
    message: str  # Message to say when triggered
    created_at: float = field(default_factory=time.time)
    triggered: bool = False

class ProactiveManager:
    """Manages reminders and watchers"""
    
    def __init__(self):
        self.reminders: List[Reminder] = []
        self.watchers: List[Watcher] = []
        self._pending_messages: List[str] = []
    
    # ========== Reminders ==========
    
    def set_reminder(self, duration_seconds: int, message: str) -> str:
        """Set a reminder that triggers after duration_seconds"""
        trigger_time = time.time() + duration_seconds
        reminder = Reminder(trigger_time=trigger_time, message=message)
        self.reminders.append(reminder)
        
        minutes = duration_seconds // 60
        seconds = duration_seconds % 60
        if minutes > 0:
            time_str = f"{minutes} dakika"
            if seconds > 0:
                time_str += f" {seconds} saniye"
        else:
            time_str = f"{seconds} saniye"
        
        return f"⏰ Hatırlatıcı kuruldu: {time_str} sonra - '{message}'"
    
    def check_reminders(self) -> List[str]:
        """Check for due reminders and return their messages"""
        due_messages = []
        remaining = []
        
        for reminder in self.reminders:
            if reminder.is_due():
                due_messages.append(f"[HATIRLATICI]: {reminder.message}")
                # Also show desktop notification
                try:
                    from plyer import notification
                    notification.notify(
                        title="⏰ Atomik Hatırlatıcı",
                        message=reminder.message,
                        app_name="Atomik",
                        timeout=15
                    )
                except Exception:
                    pass  # Notification optional
            else:
                remaining.append(reminder)
        
        self.reminders = remaining
        return due_messages
    
    def get_active_reminders(self) -> str:
        """Get list of active reminders"""
        if not self.reminders:
            return "Aktif hatırlatıcı yok."
        
        result = "⏰ Aktif hatırlatıcılar:\n"
        for r in self.reminders:
            remaining = int(r.time_remaining())
            mins = remaining // 60
            secs = remaining % 60
            result += f"• {mins}dk {secs}sn sonra: {r.message}\n"
        return result.strip()
    
    # ========== Watchers ==========
    
    def set_watcher(self, condition: str, message: str) -> str:
        """Set a watcher for a condition on screen/camera"""
        watcher = Watcher(condition=condition, message=message)
        self.watchers.append(watcher)
        return f"👁️ İzleyici kuruldu: '{condition}' olunca haber vereceğim."
    
    def get_watcher_conditions(self) -> List[str]:
        """Get list of conditions to watch for"""
        return [w.condition for w in self.watchers if not w.triggered]
    
    def trigger_watcher(self, condition: str) -> Optional[str]:
        """Trigger a watcher and return its message"""
        for watcher in self.watchers:
            if watcher.condition == condition and not watcher.triggered:
                watcher.triggered = True
                return f"[İZLEYİCİ]: {watcher.message}"
        return None
    
    def clear_triggered_watchers(self):
        """Remove triggered watchers"""
        self.watchers = [w for w in self.watchers if not w.triggered]
    
    def get_active_watchers(self) -> str:
        """Get list of active watchers"""
        active = [w for w in self.watchers if not w.triggered]
        if not active:
            return "Aktif izleyici yok."
        
        result = "👁️ Aktif izleyiciler:\n"
        for w in active:
            result += f"• {w.condition}: {w.message}\n"
        return result.strip()
    
    # ========== Pending Messages ==========
    
    def add_pending_message(self, message: str):
        """Add a message to be spoken proactively"""
        self._pending_messages.append(message)
    
    def get_pending_messages(self) -> List[str]:
        """Get and clear pending messages"""
        messages = self._pending_messages.copy()
        self._pending_messages.clear()
        return messages
    
    def has_pending(self) -> bool:
        """Check if there are pending messages or due reminders"""
        if self._pending_messages:
            return True
        for reminder in self.reminders:
            if reminder.is_due():
                return True
        return False


# Global instance
proactive_manager = ProactiveManager()


# Convenience functions
def set_reminder(duration_seconds: int, message: str) -> str:
    return proactive_manager.set_reminder(duration_seconds, message)

def set_watcher(condition: str, message: str) -> str:
    return proactive_manager.set_watcher(condition, message)

def check_proactive() -> List[str]:
    """Check all proactive triggers and return messages"""
    messages = []
    messages.extend(proactive_manager.check_reminders())
    messages.extend(proactive_manager.get_pending_messages())
    return messages

def get_watcher_conditions() -> List[str]:
    return proactive_manager.get_watcher_conditions()

def trigger_watcher(condition: str) -> Optional[str]:
    return proactive_manager.trigger_watcher(condition)
