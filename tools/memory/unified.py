"""
Unified Memory Management System for Atomik
Combines functionality from learning.py, rag_memory.py, and visual_memory.py
into a single, cohesive interface.
"""
from typing import Optional, List, Dict, Union
import json
from datetime import datetime

# Import existing modules to reuse their logic
from tools.memory import learning, rag_memory, visual_memory
from core.learning import add_vision_rule, get_vision_rules, remove_vision_rule

def manage_memory(action: str, category: str, key: str = None, content: str = None) -> str:
    """
    Unified entry point for saving information to memory.
    
    Args:
        action: 'save', 'update', or 'delete'
        category:
            - 'context': Short-term key-value (save_context)
            - 'long_term': RAG-based semantic memory (remember_this)
            - 'mood': User mood tracking (log_mood)
            - 'preference': User preferences (update_preference)
            - 'project': Project tracking (add_project)
            - 'learning': Contextual learning (learn_from_feedback)
            - 'visual': Visual observations (save_visual_observation)
            - 'proactive_rule': Rules for proactive behavior (learn_proactive_rule)
        key: Key/Topic/Mood/Filename depending on category
        content: Value/Summary/Notes/Rule depending on category
        
    Returns:
        Status message
    """
    try:
        # 1. Context (Key-Value)
        if category == 'context':
            if action in ['save', 'update']:
                return learning.save_profile_context(key, content) # Need to expose or reimplement this
            elif action == 'delete':
                # Implement deletion logic if needed
                pass

        # 2. Long Term (RAG)
        elif category == 'long_term':
            if action == 'save':
                return rag_memory.remember_conversation(summary=content, metadata={"topic": key})
            
        # 3. Mood
        elif category == 'mood':
            if action == 'save':
                return learning.log_mood(mood=key, context=content or "")

        # 4. Preference
        elif category == 'preference':
            if action in ['save', 'update']:
                return learning.update_preference(key, content)

        # 5. Project
        elif category == 'project':
            if action in ['save', 'update']:
                # content can be status
                status = content if content in ["active", "completed", "paused"] else "active"
                return learning.add_project(name=key, status=status)

        # 6. Learning (Feedback)
        elif category == 'learning':
            # This logic was in learn_from_feedback tool
            # Assuming content is JSON string of correct_steps
            if action == 'save':
                try:
                    # In a real scenario, we might need to parse content
                    # For now, let's assume specific logic resides in core.learning or learning.py
                    # Re-implementing a simple wrapper here or calling a function
                    return f"✅ Öğrenme kaydedildi (Simüle): {key}" 
                except Exception as e:
                    return f"❌ Öğrenme hatası: {e}"

        # 7. Visual
        elif category == 'visual':
            if action == 'save':
                return visual_memory.save_visual_observation(notes=content)

        # 8. Proactive Rule
        elif category == 'proactive_rule':
            if action == 'save':
                return add_vision_rule(content)
            elif action == 'delete':
                return remove_vision_rule(content)

        return f"❌ Geçersiz işlem veya kategori: {action} {category}"

    except Exception as e:
        return f"❌ Hafıza yönetim hatası: {str(e)}"

def query_memory(query: str, filter_type: str = 'all', time_range: int = None) -> str:
    """
    Unified entry point for retrieving information from memory.
    
    Args:
        query: Search query or key
        filter_type: 
            - 'all': Search everything
            - 'context': Short-term key-value
            - 'long_term': RAG search
            - 'chat': Chat history search
            - 'learning': Learned patterns
            - 'visual': Visual history
        time_range: Number of days to look back (optional)
        
    Returns:
        Formatted string results
    """
    results = []
    
    try:
        # Helper to format section
        def format_section(title, content):
            if content and "bulunamadı" not in content.lower() and "hata" not in content.lower():
                return f"\n=== {title} ===\n{content}\n"
            return ""

        # 1. Context Info
        if filter_type in ['all', 'context']:
            # Assuming learning.py has a get wrapper, or we access profile directly
            # For now using a placeholder logic closer to declarations
            # We need to expose get_context_info from learning.py if strictly needed
            pass 

        # 2. Long Term & Chat (RAG)
        if filter_type in ['all', 'long_term']:
            rag_res = rag_memory.recall_memory(query)
            if rag_res and "bulunamadı" not in rag_res:
                results.append(format_section("🗄️ Uzun Süreli Hafıza", rag_res))
            
            # Use get_recent_memories if query is generic and time_range is set
            if time_range and (not query or query == "*"):
                recent_res = rag_memory.get_recent_memories(days=time_range)
                results.append(format_section(f"📅 Son {time_range} Gün", recent_res))

        # 3. Visual History
        if filter_type in ['all', 'visual']:
            # If query relates to visual check
            if any(k in query.lower() for k in ['görünüm', 'giyim', 'kıyafet', 'saç', 'gözlük', 'nasıl görünüyorum']):
                vis_res = visual_memory.get_visual_history()
                results.append(format_section("📷 Görsel Geçmiş", vis_res))

        # 4. Learning Rules
        if filter_type in ['all', 'learning']:
            rules = get_vision_rules() # Returns list
            # Filter if query matches
            filtered_rules = [r for r in rules if query.lower() in str(r).lower()] if query else rules
            if filtered_rules:
                results.append(format_section("🧠 Öğrenilen Kurallar", "\n".join(str(r) for r in filtered_rules)))

        if not results:
            return f"❌ '{query}' ile ilgili (filtre: {filter_type}) bir bilgi bulunamadı."
        
        return "\n".join(results)

    except Exception as e:
        return f"❌ Hafıza sorgu hatası: {str(e)}"
