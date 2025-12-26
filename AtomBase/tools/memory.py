"""
Enhanced Memory System for Atomik
- Persistent conversation history
- Auto-learning user preferences
- Session summaries
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Optional

# Memory file locations
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", ".memory")
CONTEXT_FILE = os.path.join(MEMORY_DIR, "context.json")
HISTORY_FILE = os.path.join(MEMORY_DIR, "history.json")
PREFERENCES_FILE = os.path.join(MEMORY_DIR, "preferences.json")

# Ensure directory exists
os.makedirs(MEMORY_DIR, exist_ok=True)

# Max messages to keep in history
MAX_HISTORY = 50


class PersistentMemory:
    """Enhanced memory with conversation history and auto-learning"""
    
    def __init__(self):
        self.context: Dict = {}          # Explicit saves (name, preferences)
        self.history: List[Dict] = []    # Conversation history
        self.preferences: Dict = {}       # Auto-learned preferences
        self._load()
    
    def _load(self):
        """Load all memory files"""
        # Context
        try:
            if os.path.exists(CONTEXT_FILE):
                with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.context = data.get("context", {})
        except Exception:
            self.context = {}
        
        # History
        try:
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = data.get("messages", [])[-MAX_HISTORY:]
        except Exception:
            self.history = []
        
        # Preferences
        try:
            if os.path.exists(PREFERENCES_FILE):
                with open(PREFERENCES_FILE, "r", encoding="utf-8") as f:
                    self.preferences = json.load(f)
        except Exception:
            self.preferences = {}
    
    def _save_context(self):
        """Save context to file"""
        try:
            with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "context": self.context,
                    "updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Context save error: {e}")
    
    def _save_history(self):
        """Save history to file"""
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "messages": self.history[-MAX_HISTORY:],
                    "updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"History save error: {e}")
    
    def _save_preferences(self):
        """Save preferences to file"""
        try:
            with open(PREFERENCES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.preferences, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Preferences save error: {e}")
    
    # === Context (explicit saves) ===
    def save(self, key: str, value: str):
        """Save a key-value pair"""
        self.context[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }
        self._save_context()
    
    def get(self, key: str) -> Optional[str]:
        """Get a value by key"""
        if key in self.context:
            return self.context[key]["value"]
        return None
    
    def get_all(self) -> Dict:
        """Get all stored context"""
        return {k: v["value"] for k, v in self.context.items()}
    
    # === Conversation History ===
    def add_message(self, role: str, content: str):
        """Add message to history"""
        self.history.append({
            "role": role,
            "content": content[:500],  # Truncate long messages
            "time": datetime.now().strftime("%H:%M")
        })
        self._save_history()
        
        # Auto-learn from messages
        self._auto_learn(role, content)
    
    def get_recent_history(self, count: int = 10) -> List[Dict]:
        """Get recent conversation history"""
        return self.history[-count:]
    
    def get_history_summary(self) -> str:
        """Get formatted history for system prompt"""
        if not self.history:
            return ""
        
        recent = self.history[-10:]
        lines = ["[Önceki Sohbet]"]
        for msg in recent:
            role = "Sen" if msg["role"] == "user" else "Atomik"
            content = msg["content"][:100]
            lines.append(f"- {role}: {content}")
        return "\n".join(lines)
    
    # === Auto-learning ===
    def _auto_learn(self, role: str, content: str):
        """Auto-learn preferences from conversation"""
        if role != "user":
            return
        
        content_lower = content.lower()
        
        # Learn name patterns
        name_patterns = ["adım ", "benim adım ", "ben ", "ismim "]
        for pattern in name_patterns:
            if pattern in content_lower:
                idx = content_lower.find(pattern) + len(pattern)
                potential_name = content[idx:].split()[0].strip(".,!?")
                if len(potential_name) > 1 and potential_name[0].isupper():
                    self.preferences["user_name"] = potential_name
                    self._save_preferences()
                    break
        
        # Learn topics of interest
        if "topics" not in self.preferences:
            self.preferences["topics"] = []
        
        topic_keywords = {
            "kod": "programlama",
            "python": "Python",
            "oyun": "oyun geliştirme",
            "müzik": "müzik",
            "film": "filmler",
            "yemek": "yemek",
            "spor": "spor",
            "kitap": "kitaplar"
        }
        
        for keyword, topic in topic_keywords.items():
            if keyword in content_lower and topic not in self.preferences["topics"]:
                self.preferences["topics"].append(topic)
                self._save_preferences()
        
        # Learn communication style preference
        if len(content) > 100:
            self.preferences["prefers_long_responses"] = True
        elif len(content) < 20:
            self.preferences["prefers_short_responses"] = True
        self._save_preferences()
    
    def get_preferences_summary(self) -> str:
        """Get learned preferences for system prompt"""
        if not self.preferences:
            return ""
        
        lines = ["[Öğrenilen Tercihler]"]
        
        if "user_name" in self.preferences:
            lines.append(f"- Kullanıcı adı: {self.preferences['user_name']}")
        
        if self.preferences.get("topics"):
            lines.append(f"- İlgi alanları: {', '.join(self.preferences['topics'][:5])}")
        
        if self.preferences.get("prefers_short_responses"):
            lines.append("- Kısa cevaplar tercih ediyor")
        
        return "\n".join(lines) if len(lines) > 1 else ""
    
    # === Combined Context ===
    def get_full_context(self) -> str:
        """Get all context for system prompt injection"""
        parts = []
        
        # Explicit context
        context = self.get_all()
        if context:
            lines = ["[Kaydedilen Bilgiler]"]
            for key, value in context.items():
                lines.append(f"- {key}: {value}")
            parts.append("\n".join(lines))
        
        # Learned preferences
        prefs = self.get_preferences_summary()
        if prefs:
            parts.append(prefs)
        
        # Recent history
        history = self.get_history_summary()
        if history:
            parts.append(history)
        
        return "\n\n".join(parts)
    
    # === Clear ===
    def clear(self):
        """Clear all memory"""
        self.context = {}
        self.history = []
        self.preferences = {}
        self._save_context()
        self._save_history()
        self._save_preferences()
    
    def get_summary(self) -> str:
        """Get memory summary"""
        parts = []
        
        if self.context:
            parts.append(f"📝 {len(self.context)} kayıtlı bilgi")
        
        if self.history:
            parts.append(f"💬 {len(self.history)} sohbet mesajı")
        
        if self.preferences:
            parts.append(f"🧠 {len(self.preferences)} öğrenilen tercih")
        
        if not parts:
            return "Hafıza boş"
        
        return "\n".join(parts)


# Global instance
_memory = PersistentMemory()


def save_context(key: str, value: str) -> str:
    """Save context - for tool use"""
    _memory.save(key, value)
    return f"✓ '{key}' hafızaya kaydedildi"


def get_context_info(key: str) -> str:
    """Get context - for tool use"""
    value = _memory.get(key)
    if value:
        return value
    return f"'{key}' hafızada bulunamadı"


def get_memory_stats() -> str:
    """Get memory stats - for tool use"""
    return _memory.get_summary()


def clear_memory() -> str:
    """Clear memory - for tool use"""
    _memory.clear()
    return "✓ Hafıza temizlendi"


def get_all_context() -> str:
    """Get all context as string for system prompt injection"""
    return _memory.get_full_context()


def add_to_history(role: str, content: str):
    """Add message to history (called from main.py)"""
    _memory.add_message(role, content)


def get_user_name() -> Optional[str]:
    """Get learned user name"""
    return _memory.preferences.get("user_name") or _memory.get("kullanici_adi")
