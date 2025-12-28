"""
Bağlamsal Öğrenme Sistemi (Contextual Learning)
Atomik aynı hatayı tekrar yapmaz, kullanıcı düzeltmelerinden öğrenir.

Bileşenler:
- PatternDetector: Tekrarlayan davranış ve hataları tespit
- FeedbackLearner: Kullanıcı düzeltmelerinden öğrenme
- PatternMatcher: Yeni durumları öğrenilmiş kalıplarla eşleştirme
- ContextualLearningSystem: Ana orkestrasyon sınıfı
"""

import os
import sys
import json
import time
from collections import deque
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any

# Proje kökünü ekle
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# ========================================
# PATTERN DETECTOR
# ========================================

class PatternDetector:
    """
    Tekrarlayan davranışları ve hataları tespit et
    """
    
    def __init__(self, max_history: int = 1000):
        self.history = deque(maxlen=max_history)
        self.patterns = {}
    
    def record_action(
        self,
        context: str,
        actions: List[str],
        outcome: str,
        metadata: Dict = None
    ):
        """
        Her aksiyonu kaydet
        
        Args:
            context: "spotify_play", "code_write_python" vb.
            actions: ["click_play"], ["open_list", "wait", "click_play"]
            outcome: "success" / "failure"
            metadata: Ek bilgiler
        """
        record = {
            "context": context,
            "actions": actions,
            "outcome": outcome,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        self.history.append(record)
        
        # Hatalı aksiyonları analiz et
        if outcome == "failure":
            self._analyze_failure(record)
    
    def _analyze_failure(self, failed_record: Dict):
        """
        Başarısız aksiyonu analiz et
        Benzer durumlar oldu mu?
        """
        context = failed_record["context"]
        
        # Aynı context'te daha önce başarılı olan var mı?
        successful_records = [
            r for r in self.history
            if r["context"] == context and r["outcome"] == "success"
        ]
        
        if successful_records:
            # Başarılı olanla başarısız olanı karşılaştır
            successful_pattern = successful_records[-1]["actions"]
            failed_pattern = failed_record["actions"]
            
            # Farkı tespit et
            self._detect_difference(
                context=context,
                wrong_pattern=failed_pattern,
                right_pattern=successful_pattern
            )
    
    def _detect_difference(
        self,
        context: str,
        wrong_pattern: List[str],
        right_pattern: List[str]
    ):
        """
        Yanlış ve doğru arasındaki farkı bul
        """
        pattern_id = f"{context}_{int(time.time())}"
        
        self.patterns[pattern_id] = {
            "context": context,
            "wrong": wrong_pattern,
            "right": right_pattern,
            "confidence": 0.5,  # İlk tespit, düşük güven
            "corrections": 1,
            "detected_at": datetime.now().isoformat()
        }
    
    def get_recent_failures(self, context: str, limit: int = 5) -> List[Dict]:
        """Son hataları getir"""
        failures = [
            r for r in self.history
            if r["context"] == context and r["outcome"] == "failure"
        ]
        return list(failures)[-limit:]
    
    def get_success_rate(self, context: str) -> float:
        """Belirli context için başarı oranı"""
        records = [r for r in self.history if r["context"] == context]
        if not records:
            return 0.0
        
        successes = sum(1 for r in records if r["outcome"] == "success")
        return successes / len(records)


# ========================================
# FEEDBACK LEARNER
# ========================================

class FeedbackLearner:
    """
    Kullanıcı düzeltmelerinden öğren
    """
    
    def __init__(self, pattern_detector: PatternDetector, storage_path: Path = None):
        self.detector = pattern_detector
        self.learned_patterns = {}
        self.storage_path = storage_path or Path("atom_workspace/learning/patterns.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_patterns()
    
    def _load_patterns(self):
        """Kalıpları diskten yükle"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.learned_patterns = json.load(f)
            except Exception:
                self.learned_patterns = {}
    
    def _save_patterns(self):
        """Kalıpları diske kaydet"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.learned_patterns, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[FeedbackLearner] Kayıt hatası: {e}")
    
    def learn_from_correction(
        self,
        context: str,
        wrong_action: List[str],
        correct_action: List[str],
        user_feedback: str = None
    ) -> str:
        """
        Kullanıcı düzeltmesi olduğunda öğren
        
        Returns:
            pattern_id
        """
        pattern_id = self._generate_pattern_id(context)
        
        # Varsa güveni artır, yoksa yeni ekle
        if pattern_id in self.learned_patterns:
            self.learned_patterns[pattern_id]["confidence"] = min(
                1.0, self.learned_patterns[pattern_id]["confidence"] + 0.2
            )
            self.learned_patterns[pattern_id]["corrections"] += 1
            self.learned_patterns[pattern_id]["last_updated"] = datetime.now().isoformat()
        else:
            self.learned_patterns[pattern_id] = {
                "context": context,
                "wrong_pattern": wrong_action,
                "correct_pattern": correct_action,
                "user_feedback": user_feedback,
                "confidence": 0.7,  # Kullanıcı düzeltmesi → yüksek güven
                "corrections": 1,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "last_used": None,
                "success_count": 0,
                "failure_count": 0
            }
        
        self._save_patterns()
        return pattern_id
    
    def _generate_pattern_id(self, context: str) -> str:
        """Context'ten tutarlı ID üret"""
        return f"pattern_{context.lower().replace(' ', '_')}"
    
    def get_learned_pattern(self, context: str) -> Optional[Dict]:
        """Belirli bir context için öğrenilmiş kalıp var mı?"""
        pattern_id = self._generate_pattern_id(context)
        
        if pattern_id in self.learned_patterns:
            pattern = self.learned_patterns[pattern_id]
            if pattern["confidence"] > 0.6:
                return pattern
        
        return None
    
    def update_pattern_success(self, context: str):
        """Kalıp başarılı kullanıldığında güncelle"""
        pattern_id = self._generate_pattern_id(context)
        if pattern_id in self.learned_patterns:
            self.learned_patterns[pattern_id]["success_count"] += 1
            self.learned_patterns[pattern_id]["last_used"] = datetime.now().isoformat()
            # Başarı ile güveni artır
            self.learned_patterns[pattern_id]["confidence"] = min(
                1.0, self.learned_patterns[pattern_id]["confidence"] + 0.05
            )
            self._save_patterns()
    
    def update_pattern_failure(self, context: str):
        """Kalıp başarısız olduğunda güveni düşür"""
        pattern_id = self._generate_pattern_id(context)
        if pattern_id in self.learned_patterns:
            self.learned_patterns[pattern_id]["failure_count"] += 1
            self.learned_patterns[pattern_id]["confidence"] -= 0.3
            
            # Çok düşükse sil
            if self.learned_patterns[pattern_id]["confidence"] < 0.2:
                del self.learned_patterns[pattern_id]
            
            self._save_patterns()
    
    def list_all_patterns(self) -> Dict:
        """Tüm öğrenilmiş kalıpları listele"""
        return self.learned_patterns.copy()


# ========================================
# PATTERN MATCHER
# ========================================

class PatternMatcher:
    """
    Yeni durumları öğrenilmiş kalıplarla eşleştir
    """
    
    def __init__(self, feedback_learner: FeedbackLearner):
        self.learner = feedback_learner
    
    def should_apply_pattern(self, context: str) -> bool:
        """Bu context için öğrenilmiş kalıp var mı?"""
        pattern = self.learner.get_learned_pattern(context)
        return pattern is not None and pattern["confidence"] > 0.6
    
    def get_recommended_actions(self, context: str) -> Optional[List[str]]:
        """Öğrenilmiş kalıba göre aksiyon öner"""
        pattern = self.learner.get_learned_pattern(context)
        
        if pattern:
            return pattern["correct_pattern"]
        
        return None
    
    def match_similar_context(self, current_context: str) -> Optional[Dict]:
        """
        Benzer context'ler ara (fuzzy matching)
        
        Example:
            current = "youtube_play"
            learned = "spotify_play"
            → Benzer! (Her ikisi de "play")
        """
        all_patterns = self.learner.learned_patterns
        
        best_match = None
        best_score = 0
        
        for pattern_id, pattern in all_patterns.items():
            score = self._similarity_score(
                current_context,
                pattern["context"]
            )
            
            if score > best_score and score > 0.5:
                best_score = score
                best_match = pattern
        
        return best_match
    
    def _similarity_score(self, str1: str, str2: str) -> float:
        """İki string arası benzerlik (0-1)"""
        # Basit word overlap
        words1 = set(str1.lower().replace('_', ' ').split())
        words2 = set(str2.lower().replace('_', ' ').split())
        
        if not words1 or not words2:
            return 0.0
        
        overlap = len(words1 & words2)
        total = len(words1 | words2)
        
        return overlap / total if total > 0 else 0.0


# ========================================
# CONTEXTUAL LEARNING SYSTEM
# ========================================

class ContextualLearningSystem:
    """
    Ana öğrenme sistemi - Tüm bileşenleri birleştir
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'ContextualLearningSystem':
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.detector = PatternDetector()
        self.learner = FeedbackLearner(self.detector)
        self.matcher = PatternMatcher(self.learner)
    
    async def execute_with_learning(
        self,
        context: str,
        default_actions: Callable,
        action_executor: Callable = None
    ) -> Any:
        """
        Bir aksiyonu öğrenme ile birlikte yürüt
        
        Args:
            context: "spotify_play"
            default_actions: Varsayılan yapılacaklar (async callable)
            action_executor: Öğrenilmiş aksiyonları yürüten fonksiyon
        """
        # 1. Öğrenilmiş kalıp var mı kontrol et
        if self.matcher.should_apply_pattern(context):
            learned_actions = self.matcher.get_recommended_actions(context)
            
            if action_executor and learned_actions:
                try:
                    result = await action_executor(learned_actions)
                    
                    # Başarılı → Kaydet
                    self.detector.record_action(
                        context=context,
                        actions=learned_actions,
                        outcome="success"
                    )
                    self.learner.update_pattern_success(context)
                    
                    return result
                    
                except Exception as e:
                    # Başarısız → Güveni düşür
                    self.learner.update_pattern_failure(context)
                    # Varsayılana dön
                    return await default_actions()
        
        # Henüz öğrenilmemiş veya güven düşük, varsayılanı dene
        try:
            result = await default_actions()
            
            # Başarılı → Kaydet
            self.detector.record_action(
                context=context,
                actions=["default"],
                outcome="success"
            )
            
            return result
            
        except Exception as e:
            # Başarısız → Kaydet (kullanıcı düzeltsin)
            self.detector.record_action(
                context=context,
                actions=["default"],
                outcome="failure",
                metadata={"error": str(e)}
            )
            raise e
    
    def handle_user_correction(
        self,
        context: str,
        correct_steps: List[str],
        user_feedback: str = None
    ) -> str:
        """
        Kullanıcı düzeltmesi geldiğinde öğren
        
        Returns:
            pattern_id
        """
        # Son yapılan yanlış aksiyonu bul
        last_failed = None
        for record in reversed(list(self.detector.history)):
            if record["context"] == context and record["outcome"] == "failure":
                last_failed = record
                break
        
        wrong_action = last_failed["actions"] if last_failed else ["unknown"]
        
        # Öğren
        pattern_id = self.learner.learn_from_correction(
            context=context,
            wrong_action=wrong_action,
            correct_action=correct_steps,
            user_feedback=user_feedback
        )
        
        return pattern_id
    
    def forget_pattern(self, context: str) -> bool:
        """Yanlış öğrenilmiş kalıbı sil"""
        pattern_id = self.learner._generate_pattern_id(context)
        
        if pattern_id in self.learner.learned_patterns:
            del self.learner.learned_patterns[pattern_id]
            self.learner._save_patterns()
            return True
        
        return False
    
    def get_all_learned(self) -> Dict:
        """Tüm öğrenilmişleri getir"""
        return self.learner.list_all_patterns()
    
    def get_statistics(self) -> Dict:
        """Öğrenme istatistikleri"""
        patterns = self.learner.learned_patterns
        
        total_patterns = len(patterns)
        total_corrections = sum(p.get("corrections", 0) for p in patterns.values())
        total_successes = sum(p.get("success_count", 0) for p in patterns.values())
        avg_confidence = (
            sum(p.get("confidence", 0) for p in patterns.values()) / total_patterns
            if total_patterns > 0 else 0
        )
        
        return {
            "total_patterns": total_patterns,
            "total_corrections": total_corrections,
            "total_successful_uses": total_successes,
            "average_confidence": round(avg_confidence, 2),
            "history_size": len(self.detector.history)
        }


# ========================================
# TOOL FUNCTIONS
# ========================================

# Global instance
_learning_system = None

def get_learning_system() -> ContextualLearningSystem:
    """Global learning system instance"""
    global _learning_system
    if _learning_system is None:
        _learning_system = ContextualLearningSystem()
    return _learning_system


def learn_from_feedback(
    context: str,
    correct_steps: List[str],
    explanation: str = None
) -> Dict:
    """
    Kullanıcı düzeltmesinden öğren
    
    Args:
        context: "spotify_workflow", "python_code_style"
        correct_steps: ["open_list", "click_play"]
        explanation: "Önce liste aç sonra çal"
    
    Returns:
        {"status": "success", "pattern_id": "...", "message": "..."}
    """
    try:
        system = get_learning_system()
        pattern_id = system.handle_user_correction(
            context=context,
            correct_steps=correct_steps,
            user_feedback=explanation
        )
        
        return {
            "status": "success",
            "pattern_id": pattern_id,
            "message": f"Öğrendim: {context} → {correct_steps}"
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def what_did_i_learn(topic: str = None) -> Dict:
    """
    Ne öğrenilmiş göster
    
    Args:
        topic: Opsiyonel filtre (context adı)
    
    Returns:
        Öğrenilmiş kalıplar
    """
    try:
        system = get_learning_system()
        
        if topic:
            pattern = system.learner.get_learned_pattern(topic)
            if pattern:
                return {"found": True, "pattern": pattern}
            else:
                return {"found": False, "message": f"'{topic}' için öğrenilmiş kalıp yok"}
        else:
            patterns = system.get_all_learned()
            stats = system.get_statistics()
            return {
                "patterns": patterns,
                "statistics": stats
            }
    except Exception as e:
        return {"error": str(e)}


def forget_learning(context: str) -> Dict:
    """
    Öğrenileni unut (yanlış öğrenmişse)
    
    Args:
        context: Unutulacak context adı
    """
    try:
        system = get_learning_system()
        success = system.forget_pattern(context)
        
        if success:
            return {"status": "success", "message": f"Unuttum: {context}"}
        else:
            return {"status": "not_found", "message": f"'{context}' zaten öğrenilmemiş"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_learning_stats() -> Dict:
    """Öğrenme istatistiklerini getir"""
    try:
        system = get_learning_system()
        return system.get_statistics()
    except Exception as e:
        return {"error": str(e)}


# ========================================
# TEST
# ========================================

if __name__ == "__main__":
    print("=== Contextual Learning System Test ===\n")
    
    # Sistem oluştur
    system = get_learning_system()
    
    # Senaryo 1: Spotify workflow öğrenme
    print("1. Hatalı aksiyon kaydediliyor...")
    system.detector.record_action(
        context="spotify_play_ela",
        actions=["click_play"],
        outcome="failure"
    )
    
    print("2. Kullanıcı düzeltmesi alınıyor...")
    result = learn_from_feedback(
        context="spotify_play_ela",
        correct_steps=["search_ela", "click_list", "wait", "click_play"],
        explanation="Önce listeyi aç, sonra play bas"
    )
    print(f"   Sonuç: {result}")
    
    print("\n3. Ne öğrendik kontrol ediliyor...")
    learned = what_did_i_learn("spotify_play_ela")
    print(f"   Öğrenilen: {learned}")
    
    print("\n4. İstatistikler:")
    stats = get_learning_stats()
    print(f"   {stats}")
    
    print("\n5. Benzer context aranıyor...")
    similar = system.matcher.match_similar_context("youtube_play")
    print(f"   Benzer kalıp: {similar}")
    
    print("\n✅ Test tamamlandı!")
