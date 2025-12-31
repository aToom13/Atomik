"""
SQLite Session History for Atomik
Stores all conversations in a persistent database.
"""
import os
import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json

# Database path
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", ".memory")
os.makedirs(MEMORY_DIR, exist_ok=True)
DB_PATH = os.path.join(MEMORY_DIR, "sessions.db")

# Global connection
_conn = None


def _get_conn():
    """Get or create database connection"""
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _init_db()
    return _conn


def _init_db():
    """Initialize database tables"""
    conn = _get_conn()
    cursor = conn.cursor()
    
    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            summary TEXT,
            message_count INTEGER DEFAULT 0
        )
    """)
    
    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    
    # Create index for faster searches
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_messages_content 
        ON messages(content)
    """)
    
    conn.commit()


# Current session ID
_current_session_id = None


def start_session() -> int:
    """Start a new conversation session"""
    global _current_session_id
    
    conn = _get_conn()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO sessions (start_time) VALUES (?)",
        (now,)
    )
    conn.commit()
    
    _current_session_id = cursor.lastrowid
    return _current_session_id


def end_session(summary: str = None):
    """End current session"""
    global _current_session_id
    
    if _current_session_id is None:
        return
    
    conn = _get_conn()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    cursor.execute(
        "UPDATE sessions SET end_time = ?, summary = ? WHERE id = ?",
        (now, summary, _current_session_id)
    )
    conn.commit()
    
    _current_session_id = None


def save_message(role: str, content: str) -> int:
    """Save a message to current session"""
    global _current_session_id
    
    # Auto-start session if needed
    if _current_session_id is None:
        start_session()
    
    conn = _get_conn()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (_current_session_id, role, content[:1000], now)  # Truncate long messages
    )
    
    # Update message count
    cursor.execute(
        "UPDATE sessions SET message_count = message_count + 1 WHERE id = ?",
        (_current_session_id,)
    )
    
    conn.commit()
    return cursor.lastrowid


def get_session_history(session_id: int = None) -> List[Dict]:
    """Get messages from a session"""
    conn = _get_conn()
    cursor = conn.cursor()
    
    sid = session_id or _current_session_id
    if sid is None:
        return []
    
    cursor.execute(
        "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY timestamp",
        (sid,)
    )
    
    return [dict(row) for row in cursor.fetchall()]


def search_history(query: str, limit: int = 10) -> str:
    """Search all messages for a query"""
    conn = _get_conn()
    cursor = conn.cursor()
    
    # Simple LIKE search (SQLite doesn't have full-text by default)
    cursor.execute("""
        SELECT m.role, m.content, m.timestamp, s.id as session_id
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        WHERE m.content LIKE ?
        ORDER BY m.timestamp DESC
        LIMIT ?
    """, (f"%{query}%", limit))
    
    results = cursor.fetchall()
    
    if not results:
        return f"'{query}' ile ilgili geçmiş konuşma bulunamadı."
    
    output = f"🔍 '{query}' için {len(results)} sonuç:\n"
    for row in results:
        role = "Sen" if row["role"] == "user" else "Atomik"
        date = row["timestamp"][:10]
        content = row["content"][:100]
        output += f"\n📅 {date} | {role}: {content}..."
    
    return output


def get_recent_sessions(limit: int = 5) -> str:
    """Get list of recent sessions"""
    conn = _get_conn()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, start_time, end_time, summary, message_count
        FROM sessions
        ORDER BY start_time DESC
        LIMIT ?
    """, (limit,))
    
    results = cursor.fetchall()
    
    if not results:
        return "Henüz kayıtlı oturum yok."
    
    output = f"📋 Son {len(results)} oturum:\n"
    for row in results:
        date = row["start_time"][:16].replace("T", " ")
        count = row["message_count"]
        summary = row["summary"] or "Özet yok"
        output += f"\n• {date} ({count} mesaj): {summary[:50]}"
    
    return output


def get_stats() -> str:
    """Get conversation statistics"""
    conn = _get_conn()
    cursor = conn.cursor()
    
    # Total sessions
    cursor.execute("SELECT COUNT(*) FROM sessions")
    total_sessions = cursor.fetchone()[0]
    
    # Total messages
    cursor.execute("SELECT COUNT(*) FROM messages")
    total_messages = cursor.fetchone()[0]
    
    # Messages by role
    cursor.execute("SELECT role, COUNT(*) FROM messages GROUP BY role")
    by_role = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Today's messages
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        "SELECT COUNT(*) FROM messages WHERE timestamp LIKE ?",
        (f"{today}%",)
    )
    today_count = cursor.fetchone()[0]
    
    return f"""📊 Sohbet İstatistikleri:
• Toplam oturum: {total_sessions}
• Toplam mesaj: {total_messages}
• Senin mesajların: {by_role.get('user', 0)}
• Atomik cevapları: {by_role.get('agent', 0)} 
• Bugünkü mesajlar: {today_count}"""


def clear_all_history() -> str:
    """Clear all conversation history"""
    conn = _get_conn()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM messages")
    cursor.execute("DELETE FROM sessions")
    conn.commit()
    
    return "✅ Tüm sohbet geçmişi silindi."


def get_recent_context(limit: int = 15) -> List[Dict]:
    """
    Get recent messages across ALL sessions for context restoration.
    Used to restore memory after a restart/crash.
    """
    conn = _get_conn()
    cursor = conn.cursor()
    
    # Get last N messages regarding of session
    cursor.execute("""
        SELECT role, content, timestamp 
        FROM messages 
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    
    # Return in reverse order (oldest first) for conversation flow
    rows = cursor.fetchall()
    results = [dict(row) for row in rows]
    return results[::-1]
