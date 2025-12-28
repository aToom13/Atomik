"""
RAG Memory System for Atomik
Uses ChromaDB for vector storage and Gemini embeddings for semantic search.
Remembers conversations across sessions.
"""
import os
import json
from datetime import datetime
from typing import List, Optional
import hashlib

# ChromaDB for vector storage
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

# Gemini for embeddings
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# Memory directory
MEMORY_DIR = os.path.join(os.path.dirname(__file__), "..", ".memory")
CHROMA_DIR = os.path.join(MEMORY_DIR, "chroma_db")
os.makedirs(CHROMA_DIR, exist_ok=True)

# Global instances
_client = None
_collection = None


def _get_client():
    """Get or create ChromaDB client"""
    global _client
    if _client is None and CHROMADB_AVAILABLE:
        _client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
    return _client


def _get_collection():
    """Get or create conversation memory collection"""
    global _collection
    if _collection is None:
        client = _get_client()
        if client:
            _collection = client.get_or_create_collection(
                name="conversation_memory",
                metadata={"description": "Atomik conversation memories"}
            )
    return _collection


def _generate_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding using Gemini API"""
    if not GENAI_AVAILABLE:
        return None
    
    try:
        # Configure with existing API key from environment
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None
        
        genai.configure(api_key=api_key)
        
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    except Exception as e:
        print(f"Embedding error: {e}")
        return None


def _generate_id(text: str) -> str:
    """Generate unique ID for a memory"""
    timestamp = datetime.now().isoformat()
    return hashlib.md5(f"{text}_{timestamp}".encode()).hexdigest()[:16]


# ============== PUBLIC API ==============

def remember_conversation(summary: str, metadata: dict = None) -> str:
    """
    Save a conversation summary to long-term memory.
    
    Args:
        summary: Brief summary of what was discussed
        metadata: Optional metadata (topic, date, etc.)
    
    Returns:
        Status message
    """
    if not CHROMADB_AVAILABLE:
        return "❌ ChromaDB yüklü değil. `pip install chromadb` çalıştır."
    
    collection = _get_collection()
    if not collection:
        return "❌ Hafıza veritabanı açılamadı."
    
    # Prepare metadata
    meta = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
    }
    if metadata:
        meta.update(metadata)
    
    # Generate embedding
    embedding = _generate_embedding(summary)
    
    # Generate unique ID
    doc_id = _generate_id(summary)
    
    try:
        if embedding:
            collection.add(
                ids=[doc_id],
                documents=[summary],
                embeddings=[embedding],
                metadatas=[meta]
            )
        else:
            # Fallback: add without embedding (will use default)
            collection.add(
                ids=[doc_id],
                documents=[summary],
                metadatas=[meta]
            )
        
        return f"✅ Hafızaya kaydedildi: {summary[:50]}..."
    except Exception as e:
        return f"❌ Kayıt hatası: {str(e)}"


def recall_memory(query: str, n_results: int = 3) -> str:
    """
    Search long-term memory for relevant conversations.
    
    Args:
        query: What to search for (semantic search)
        n_results: Maximum number of results
    
    Returns:
        Relevant memories or "nothing found"
    """
    if not CHROMADB_AVAILABLE:
        return "ChromaDB yüklü değil."
    
    collection = _get_collection()
    if not collection:
        return "Hafıza veritabanı açılamadı."
    
    # Check if collection is empty
    if collection.count() == 0:
        return "Hafızada kayıtlı anı yok."
    
    try:
        # Generate query embedding
        query_embedding = _generate_embedding(query)
        
        if query_embedding:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, collection.count())
            )
        else:
            # Fallback: text search
            results = collection.query(
                query_texts=[query],
                n_results=min(n_results, collection.count())
            )
        
        if not results["documents"] or not results["documents"][0]:
            return f"'{query}' ile ilgili bir anı bulunamadı."
        
        # Format results
        memories = []
        for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0])):
            date = meta.get("date", "?")
            time = meta.get("time", "?")
            memories.append(f"📅 {date} {time}: {doc}")
        
        return "🧠 Hatırlıyorum:\n" + "\n".join(memories)
    
    except Exception as e:
        return f"Arama hatası: {str(e)}"


def get_memory_count() -> int:
    """Get total number of stored memories"""
    collection = _get_collection()
    if collection:
        return collection.count()
    return 0


def clear_all_memories() -> str:
    """Clear all stored memories (use with caution!)"""
    global _collection
    
    client = _get_client()
    if client:
        try:
            client.delete_collection("conversation_memory")
            _collection = None
            return "✅ Tüm anılar silindi."
        except Exception as e:
            return f"❌ Silme hatası: {str(e)}"
    return "❌ Veritabanı bağlantısı yok."


def get_recent_memories(days: int = 7) -> str:
    """Get memories from the last N days"""
    if not CHROMADB_AVAILABLE:
        return "ChromaDB yüklü değil."
    
    collection = _get_collection()
    if not collection or collection.count() == 0:
        return "Hafızada kayıt yok."
    
    try:
        # Get all and filter by date
        all_memories = collection.get(include=["documents", "metadatas"])
        
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        recent = []
        for doc, meta in zip(all_memories["documents"], all_memories["metadatas"]):
            if meta.get("date", "") >= cutoff:
                date = meta.get("date", "?")
                time = meta.get("time", "?")
                recent.append(f"📅 {date} {time}: {doc}")
        
        if not recent:
            return f"Son {days} günde kayıtlı anı yok."
        
        return f"🧠 Son {days} günün anıları:\n" + "\n".join(recent[-10:])  # Last 10
    
    except Exception as e:
        return f"Hata: {str(e)}"
