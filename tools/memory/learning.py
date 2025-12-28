"""
Learning System for Atomik
Handles memory, fact extraction, user profile, and mood tracking.
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Profile path
# Profile path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEMORY_DIR = os.path.join(BASE_DIR, "AtomBase", ".memory")
PROFILE_PATH = os.path.join(MEMORY_DIR, "user_profile.json")

# Default profile template
DEFAULT_PROFILE = {
    "name": "Akif",
    "preferences": {},
    "projects": [],
    "facts": [],
    "mood_log": [],
    "last_updated": None
}


# ============================================
# USER PROFILE MANAGEMENT
# ============================================

def load_profile() -> Dict:
    """Load user profile from JSON file."""
    try:
        if os.path.exists(PROFILE_PATH):
            with open(PROFILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return DEFAULT_PROFILE.copy()


def save_profile(profile: Dict) -> bool:
    """Save user profile to JSON file."""
    try:
        os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
        profile["last_updated"] = datetime.now().isoformat()
        with open(PROFILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def update_preference(key: str, value: str) -> str:
    """Update a user preference."""
    profile = load_profile()
    profile["preferences"][key] = value
    save_profile(profile)
    return f"✅ Tercih kaydedildi: {key} = {value}"


def add_project(name: str, status: str = "active") -> str:
    """Add or update a project."""
    profile = load_profile()
    
    # Check if project exists
    for project in profile["projects"]:
        if project["name"].lower() == name.lower():
            project["status"] = status
            project["updated"] = datetime.now().isoformat()
            save_profile(profile)
            return f"✅ Proje güncellendi: {name} → {status}"
    
    # Add new project
    profile["projects"].append({
        "name": name,
        "status": status,
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat()
    })
    save_profile(profile)
    return f"✅ Yeni proje eklendi: {name}"


def add_fact(fact: str) -> str:
    """Add a fact about the user."""
    profile = load_profile()
    if fact not in profile["facts"]:
        profile["facts"].append(fact)
        save_profile(profile)
        return f"✅ Bilgi kaydedildi: {fact}"
    return "Bu bilgi zaten kayıtlı."


# ============================================
# MOOD TRACKING
# ============================================

VALID_MOODS = ["happy", "sad", "tired", "focused", "stressed", "relaxed", "neutral"]

def log_mood(mood: str, context: str = "") -> str:
    """Log user's mood with optional context."""
    profile = load_profile()
    
    mood = mood.lower()
    if mood not in VALID_MOODS:
        mood = "neutral"
    
    entry = {
        "mood": mood,
        "context": context,
        "timestamp": datetime.now().isoformat()
    }
    
    profile["mood_log"].append(entry)
    
    # Keep only last 100 entries
    if len(profile["mood_log"]) > 100:
        profile["mood_log"] = profile["mood_log"][-100:]
    
    save_profile(profile)
    return f"✅ Ruh hali kaydedildi: {mood}"


def get_mood_history(days: int = 7) -> str:
    """Get mood history for the last N days."""
    profile = load_profile()
    
    cutoff = datetime.now() - timedelta(days=days)
    recent = []
    
    for entry in profile["mood_log"]:
        try:
            ts = datetime.fromisoformat(entry["timestamp"])
            if ts >= cutoff:
                recent.append(entry)
        except:
            pass
    
    if not recent:
        return "Son günlerde mood kaydı yok."
    
    # Summarize
    mood_counts = {}
    for entry in recent:
        mood = entry["mood"]
        mood_counts[mood] = mood_counts.get(mood, 0) + 1
    
    summary = ", ".join([f"{m}: {c}x" for m, c in mood_counts.items()])
    return f"📊 Son {days} gün: {summary}"


# ============================================
# STARTUP CONTEXT
# ============================================

def get_startup_context() -> str:
    """Get context to inject at session start."""
    parts = []
    
    # Header - CRITICAL: Tell AI this is background info, NOT tasks to continue
    parts.append("⚠️ ÖNEMLİ: Aşağıdaki bilgiler ARKA PLAN BİLGİSİDİR. Bunlar eski oturumlardan geliyor.")
    parts.append("❌ Bu bilgilerden DEVAM ETME. Kullanıcı yeni bir konuşma başlatıyor.")
    parts.append("✅ Sadece referans olarak kullan, sorulursa hatırla.")
    parts.append("")
    
    # 1. Load profile
    profile = load_profile()
    
    # 2. User info
    if profile["name"]:
        parts.append(f"👤 Kullanıcı: {profile['name']}")
    
    # 3. Preferences
    if profile["preferences"]:
        prefs = ", ".join([f"{k}: {v}" for k, v in list(profile["preferences"].items())[:5]])
        parts.append(f"⚙️ Tercihler: {prefs}")
    
    # 4. Active projects (info only, don't continue)
    active_projects = [p for p in profile["projects"] if p.get("status") != "completed"]
    if active_projects:
        proj_list = ", ".join([f"{p['name']} ({p.get('status', 'active')})" for p in active_projects[:3]])
        parts.append(f"📂 Bilinen projeler: {proj_list}")
    
    # 5. Recent mood
    if profile["mood_log"]:
        last_mood = profile["mood_log"][-1]
        parts.append(f"😊 Son mood: {last_mood['mood']}")
    
    # 6. Key facts
    if profile["facts"]:
        facts = "; ".join(profile["facts"][:3])
        parts.append(f"📝 Bilgiler: {facts}")
    
    # 7. SKIP recent memories to avoid "continuing" old tasks
    # These were causing the AI to try to continue old conversations
    # Only load if explicitly requested by user
    
    if len(parts) <= 4:  # Only header lines
        return ""
    
    parts.append("")
    parts.append("🆕 Yeni oturum başladı. Kullanıcıyı selamla ve NE İSTEDİĞİNİ SOR.")
    
    return "\n".join(parts)


# ============================================
# FACT EXTRACTION (Simple keyword-based)
# ============================================

def extract_facts_from_text(text: str) -> List[Dict]:
    """Extract facts from conversation text using simple patterns."""
    facts = []
    text_lower = text.lower()
    
    # Preference patterns
    preference_keywords = {
        "favori": "preference",
        "seviyorum": "preference", 
        "tercih": "preference",
        "beğeniyorum": "preference"
    }
    
    # Project patterns
    project_keywords = {
        "proje": "project",
        "üzerinde çalış": "project",
        "geliştir": "project",
        "yap": "project"
    }
    
    # Check for preferences
    for keyword, fact_type in preference_keywords.items():
        if keyword in text_lower:
            facts.append({
                "type": fact_type,
                "raw": text[:100],
                "confidence": 0.6
            })
            break
    
    # Check for projects
    for keyword, fact_type in project_keywords.items():
        if keyword in text_lower:
            facts.append({
                "type": fact_type,
                "raw": text[:100],
                "confidence": 0.5
            })
            break
    
    return facts


def process_conversation_for_learning(user_msg: str, agent_msg: str) -> None:
    """Process a conversation turn and extract learnable information."""
    try:
        combined = f"Kullanıcı: {user_msg}\nAsistan: {agent_msg}"
        facts = extract_facts_from_text(combined)
        
        # For now, just log high-confidence facts
        for fact in facts:
            if fact["confidence"] >= 0.7:
                add_fact(fact["raw"][:50])
    except:
        pass  # Fail silently
