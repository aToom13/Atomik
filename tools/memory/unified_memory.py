"""
Unified Memory System - 3-Layer Architecture
============================================
Katman 1: Working Memory (RAM) - Son 1 saat, hızlı erişim
Katman 2: Episodic Memory (Events) - ChromaDB ile uzun süreli anılar
Katman 3: Semantic Memory (Knowledge) - JSON ile kalıcı bilgiler
"""
import os
import time
import json
import random
import logging
from collections import deque
from datetime import datetime
from typing import Dict, List, Any, Optional

# Project root setup
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(_project_root, "data", "memory")
os.makedirs(DATA_DIR, exist_ok=True)

logger = logging.getLogger("atomik.memory")


# =============================================================================
# KATMAN 1: WORKING MEMORY (Kısa Süreli Hafıza)
# =============================================================================
class WorkingMemory:
    """
    Son 1 saatin bilgilerini tutar.
    Hızlı erişim, geçici saklama.
    deque tabanlı, TTL (time-to-live) destekli.
    """
    
    def __init__(self, max_items: int = 100, ttl_seconds: int = 3600):
        self.memory: deque = deque(maxlen=max_items)
        self.ttl = ttl_seconds
        self._load_from_disk()
    
    def add(self, item: Dict):
        """
        Zaman damgalı kayıt ekle
        """
        item['_timestamp'] = time.time()
        item['_ttl'] = self.ttl
        self.memory.append(item)
        self._save_to_disk()
    
    def get_recent(self, n: int = 10) -> List[Dict]:
        """
        Son N kaydı getir (süresi dolmamış)
        """
        now = time.time()
        valid = [
            item for item in self.memory
            if now - item.get('_timestamp', 0) < item.get('_ttl', self.ttl)
        ]
        return list(valid)[-n:]
    
    def search(self, query: str) -> List[Dict]:
        """
        Basit metin araması
        """
        query_lower = query.lower()
        results = []
        for item in self.memory:
            if query_lower in str(item).lower():
                results.append(item)
        return results
    
    def clear_expired(self):
        """
        Süresi dolmuş kayıtları temizle
        """
        now = time.time()
        valid_items = [
            item for item in self.memory
            if now - item.get('_timestamp', 0) < item.get('_ttl', self.ttl)
        ]
        self.memory.clear()
        self.memory.extend(valid_items)
        self._save_to_disk()
    
    def _save_to_disk(self):
        """Diske kaydet (crash recovery için)"""
        try:
            filepath = os.path.join(DATA_DIR, "working_memory.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(list(self.memory), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Working memory save error: {e}")
    
    def _load_from_disk(self):
        """Diskten yükle"""
        try:
            filepath = os.path.join(DATA_DIR, "working_memory.json")
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    items = json.load(f)
                    self.memory.extend(items)
                    self.clear_expired()  # Eski kayıtları temizle
        except Exception as e:
            logger.error(f"Working memory load error: {e}")


# =============================================================================
# KATMAN 2: EPISODIC MEMORY (Uzun Süreli Olaylar)
# =============================================================================
class EpisodicMemory:
    """
    Uzun süreli olay bazlı hafıza.
    ChromaDB ile vektör arama (varsa), yoksa basit JSON fallback.
    """
    
    def __init__(self):
        self.use_chroma = False
        self.collection = None
        self.embedder = None
        self._fallback_episodes = []  # ChromaDB yokken kullan
        
        self._init_backend()
    
    def _init_backend(self):
        """ChromaDB veya fallback backend başlat"""
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
            
            persist_dir = os.path.join(DATA_DIR, "chroma_db")
            self.client = chromadb.PersistentClient(path=persist_dir)
            self.collection = self.client.get_or_create_collection(
                name="atomik_episodes",
                metadata={"hnsw:space": "cosine"}
            )
            
            # Embedding model (küçük ve hızlı)
            self.embedder = SentenceTransformer('paraphrase-MiniLM-L6-v2')
            self.use_chroma = True
            logger.info("EpisodicMemory: ChromaDB backend active")
            
        except ImportError:
            logger.warning("EpisodicMemory: ChromaDB/SentenceTransformers not found. Using JSON fallback.")
            self._load_fallback()
    
    def save_episode(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        importance: float = 0.5
    ):
        """
        Bir olayı kalıcı olarak kaydet
        """
        # Önemsiz olayları kaydetme
        if importance < 0.3:
            return
        
        metadata = metadata or {}
        metadata['importance'] = importance
        metadata['timestamp'] = time.time()
        metadata['date'] = datetime.now().isoformat()
        
        if self.use_chroma:
            try:
                embedding = self.embedder.encode(content).tolist()
                episode_id = f"ep_{int(time.time() * 1000)}"
                
                self.collection.add(
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[metadata],
                    ids=[episode_id]
                )
                return f"✅ Hafızaya kaydedildi (Episode): {content[:50]}..."
            except Exception as e:
                logger.error(f"ChromaDB save error: {e}")
                self._save_to_fallback(content, metadata)
                return f"⚠️ Fallback'e kaydedildi (Hata: {e})"
        else:
            self._save_to_fallback(content, metadata)
            return f"✅ Hafızaya kaydedildi (Fallback): {content[:50]}..."
    
    def recall(
        self,
        query: str,
        n_results: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Semantik arama ile anıları getir
        """
        if self.use_chroma:
            try:
                query_embedding = self.embedder.encode(query).tolist()
                
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=filters
                )
                
                episodes = []
                if results['documents'] and results['documents'][0]:
                    for i, doc in enumerate(results['documents'][0]):
                        episodes.append({
                            "content": doc,
                            "metadata": results['metadatas'][0][i] if results['metadatas'] else {}
                        })
                return episodes
                
            except Exception as e:
                logger.error(f"ChromaDB query error: {e}")
                return self._search_fallback(query)
        else:
            return self._search_fallback(query)
    
    def _save_to_fallback(self, content: str, metadata: Dict):
        """JSON fallback'e kaydet"""
        self._fallback_episodes.append({
            "content": content,
            "metadata": metadata
        })
        self._persist_fallback()
    
    def _search_fallback(self, query: str) -> List[Dict]:
        """Fallback'te basit arama"""
        query_lower = query.lower()
        results = []
        for ep in self._fallback_episodes:
            if query_lower in ep['content'].lower():
                results.append(ep)
        return results[-5:]  # Son 5
    
    def _persist_fallback(self):
        """Fallback verisini diske yaz"""
        try:
            filepath = os.path.join(DATA_DIR, "episodic_fallback.json")
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self._fallback_episodes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Fallback persist error: {e}")
    
    def _load_fallback(self):
        """Fallback verisini diskten oku"""
        try:
            filepath = os.path.join(DATA_DIR, "episodic_fallback.json")
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    self._fallback_episodes = json.load(f)
        except Exception as e:
            logger.error(f"Fallback load error: {e}")


# =============================================================================
# KATMAN 3: SEMANTIC MEMORY (Kalıcı Bilgiler)
# =============================================================================
class SemanticMemory:
    """
    Kalıcı bilgiler ve öğrenilmiş kalıplar.
    JSON tabanlı, hızlı erişim.
    """
    
    def __init__(self, filepath: Optional[str] = None):
        self.filepath = filepath or os.path.join(DATA_DIR, "semantic_memory.json")
        self.memory = self._load()
    
    def _load(self) -> Dict:
        """JSON'dan yükle"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Semantic memory load error: {e}")
        return self._default_structure()
    
    def _default_structure(self) -> Dict:
        """Varsayılan boş yapı"""
        return {
            "user_profile": {
                "name": None,
                "preferences": {}
            },
            "relationships": {},
            "learned_patterns": {},
            "projects": {},
            "custom": {}
        }
    
    def update(self, path: str, value: Any):
        """
        Nested path ile güncelle
        
        Example:
            update("user_profile.name", "Akif")
            update("relationships.Ela.status", "girlfriend")
        """
        keys = path.split('.')
        current = self.memory
        
        # Son key'e kadar ilerle, yoksa oluştur
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Son key'i güncelle
        current[keys[-1]] = value
        self._save()
    
    def get(self, path: str, default=None) -> Any:
        """
        Nested path ile getir
        """
        keys = path.split('.')
        current = self.memory
        
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        
        return current
    
    def delete(self, path: str) -> bool:
        """
        Path'deki değeri sil
        """
        keys = path.split('.')
        current = self.memory
        
        for key in keys[:-1]:
            if key not in current:
                return False
            current = current[key]
        
        if keys[-1] in current:
            del current[keys[-1]]
            self._save()
            return True
        return False
    
    def list_all(self) -> Dict:
        """Tüm içeriği döndür"""
        return self.memory
    
    def _save(self):
        """JSON'a kaydet"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Semantic memory save error: {e}")


# =============================================================================
# UNIFIED MEMORY SYSTEM (3 Katman Entegrasyonu)
# =============================================================================
class UnifiedMemorySystem:
    """
    3 katmanı birleştiren ana sistem.
    Akıllı yönlendirme ve konsolidasyon.
    """
    
    def __init__(self):
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        logger.info("UnifiedMemorySystem initialized with 3 layers")
    
    def remember(self, item: Dict):
        """
        Akıllı hafıza yönetimi
        
        Args:
            item: {
                "type": "conversation" | "preference" | "event" | "fact",
                "content": str,
                "importance": 0-1,
                "metadata": {},
                "path": "semantic.path.if.preference"
            }
        """
        # 1. Her şey önce working memory'ye
        self.working.add(item)
        
        # 2. Önemliyse episodic'e kaydet
        importance = item.get('importance', 0.5)
        if importance > 0.5:
            self.episodic.save_episode(
                content=item.get('content', str(item)),
                metadata=item.get('metadata', {}),
                importance=importance
            )
        
        # 3. Tercih/bilgi ise semantic'e
        if item.get('type') == 'preference' and 'path' in item:
            self.semantic.update(
                item['path'],
                item.get('value', item.get('content'))
            )
    
    def recall(self, query: str, mode: str = "auto") -> Dict:
        """
        Akıllı hatırlama
        
        Modes:
            - auto: Otomatik karar (tümünden ara)
            - recent: Sadece working memory
            - episodic: Uzun süreli anılar
            - semantic: Kalıcı bilgiler
        """
        results = {
            "working": [],
            "episodic": [],
            "semantic": None,
            "source": mode
        }
        
        if mode in ["auto", "recent"]:
            results["working"] = self.working.search(query)
        
        if mode in ["auto", "episodic"]:
            results["episodic"] = self.episodic.recall(query)
        
        if mode in ["auto", "semantic"]:
            # Query'den path çıkarmaya çalış
            path = self._extract_semantic_path(query)
            if path:
                results["semantic"] = self.semantic.get(path)
        
        return results
    
    def _extract_semantic_path(self, query: str) -> Optional[str]:
        """
        Query'den semantic path çıkar
        Örn: "Ela'nın durumu" → "relationships.Ela"
        """
        query_lower = query.lower()
        
        # Basit kural tabanlı çıkarım
        if "profil" in query_lower or "isim" in query_lower:
            return "user_profile"
        elif "tercih" in query_lower or "preference" in query_lower:
            return "user_profile.preferences"
        elif "proje" in query_lower:
            return "projects"
        
        # İsim araması
        for key in self.semantic.memory.get("relationships", {}).keys():
            if key.lower() in query_lower:
                return f"relationships.{key}"
        
        return None
    
    def get_context_for_prompt(self, max_items: int = 5) -> str:
        """
        Prompt'a eklenecek bağlam bilgisi oluştur
        """
        context_parts = []
        
        # Son konuşmalar
        recent = self.working.get_recent(max_items)
        if recent:
            conv_summary = [
                f"- {item.get('type', 'item')}: {str(item.get('content', ''))[:100]}"
                for item in recent
            ]
            context_parts.append("Son konuşmalar:\n" + "\n".join(conv_summary))
        
        # Kullanıcı profili
        profile = self.semantic.get("user_profile", {})
        if profile.get("name"):
            context_parts.append(f"Kullanıcı: {profile.get('name')}")
        
        return "\n\n".join(context_parts)
    
    def consolidate_daily(self) -> str:
        """
        Günlük hafıza konsolidasyonu.
        Working memory'den önemli bilgileri episodic'e taşır.
        """
        items = self.working.get_recent(100)
        consolidated = 0
        
        for item in items:
            importance = item.get('importance', 0.3)
            if importance > 0.6:
                self.episodic.save_episode(
                    content=item.get('content', str(item)),
                    metadata=item.get('metadata', {}),
                    importance=importance
                )
                consolidated += 1
        
        # Süresi dolmuş kayıtları temizle
        self.working.clear_expired()
        
        return f"Konsolidasyon tamamlandı: {consolidated} önemli kayıt episodic memory'ye taşındı."


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================
memory_system: Optional[UnifiedMemorySystem] = None


def get_memory_system() -> UnifiedMemorySystem:
    """Global memory system instance"""
    global memory_system
    if memory_system is None:
        memory_system = UnifiedMemorySystem()
    return memory_system
