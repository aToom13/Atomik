"""
Learning Module for Atomik
Manages user preferences and feedback for proactive behavior.
Stores rules in a JSON file to be used by Vision Analyzer.
"""
import json
import os

FEEDBACK_FILE = os.path.join(os.path.dirname(__file__), "feedback.json")

def load_feedback_rules() -> list:
    """Load all learned rules from the JSON file."""
    if not os.path.exists(FEEDBACK_FILE):
        return []
    try:
        with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("vision_rules", [])
    except Exception as e:
        print(f"Error loading feedback: {e}")
        return []

def add_vision_rule(rule: str) -> str:
    """Add a new rule for vision analyzer behavior."""
    rules = load_feedback_rules()
    if rule not in rules:
        rules.append(rule)
        
    try:
        with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
            json.dump({"vision_rules": rules}, f, indent=2, ensure_ascii=False)
        return f"Kural öğrenildi: '{rule}'"
    except Exception as e:
        return f"Kural kaydedilemedi: {e}"

def get_formatted_rules() -> str:
    """Get rules formatted for the prompt."""
    rules = load_feedback_rules()
    if not rules:
        return ""
    
    formatted = "\n## KULLANICI ÖZEL KURALLARI (BUNLARA KESİN UY):\n"
    for rule in rules:
        formatted += f"- {rule}\n"
    return formatted

def get_vision_rules() -> list:
    """Load vision rules (alias for load_feedback_rules)."""
    return load_feedback_rules()

def remove_vision_rule(rule: str) -> str:
    """Remove a specific vision rule."""
    rules = load_feedback_rules()
    if rule in rules:
        rules.remove(rule)
        try:
            with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
                json.dump({"vision_rules": rules}, f, indent=2, ensure_ascii=False)
            return f"Kural silindi: '{rule}'"
        except Exception as e:
            return f"Kaydetme hatası: {e}"
    return "Kural bulunamadı."

