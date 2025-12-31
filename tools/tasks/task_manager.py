"""
Otonom Görev Yönetim Sistemi (Autonomous Task Manager)
Atomik görev listesi tutar, sormadan hatırlatır, proaktif yardım eder.

Bileşenler:
- TaskNLU: Doğal dilden görev çıkarma
- TaskDatabase: Görev saklama ve yönetimi
- TaskScheduler: Zamanlayıcı ve hatırlatıcılar
- AutonomousTaskManager: Ana orkestrasyon sınıfı
"""

import os
import sys
import json
import time
import asyncio
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict

# Proje kökünü ekle
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ========================================
# TASK NLU (Natural Language Understanding)
# ========================================

class TaskNLU:
    """
    Konuşmadan görev çıkar
    """
    
    def __init__(self):
        # Görev belirteçleri
        self.task_indicators = [
            "lazım", "gerek", "yapmalıyım", "almalıyım",
            "gitmeliyim", "aramam lazım", "unutma",
            "hatırlat", "yarın", "bugün", "gelecek hafta",
            "must", "need to", "have to", "should",
            "remind me", "don't forget", "tomorrow", "today"
        ]
        
        # Öncelik belirteçleri
        self.urgency_keywords = {
            "high": ["acil", "hemen", "şimdi", "urgent", "asap", "kritik"],
            "medium": ["önemli", "gerekli", "important"],
            "low": ["belki", "bir ara", "maybe", "sometime"]
        }
        
        # Kategori anahtar kelimeleri
        self.category_keywords = {
            "work": ["proje", "iş", "toplantı", "meeting", "code", "kod", "deadline"],
            "personal": ["kişisel", "özel", "personal"],
            "shopping": ["al", "satın", "hediye", "buy", "gift", "market"],
            "health": ["doktor", "ilaç", "spor", "sağlık", "doctor", "medicine"],
            "social": ["ara", "ziyaret", "buluş", "call", "visit", "meet"]
        }
        
        # Zaman ifadeleri
        self.time_patterns = {
            "yarın": timedelta(days=1),
            "bugün": timedelta(days=0),
            "haftaya": timedelta(weeks=1),
            "gelecek hafta": timedelta(weeks=1),
            "tomorrow": timedelta(days=1),
            "today": timedelta(days=0),
            "next week": timedelta(weeks=1),
        }
    
    def detect_task(self, text: str) -> bool:
        """Bu cümlede görev var mı?"""
        text_lower = text.lower()
        return any(
            indicator in text_lower 
            for indicator in self.task_indicators
        )
    
    def extract_task(self, text: str) -> Optional[Dict]:
        """
        Cümleden görev bilgilerini çıkar (basit parsing)
        
        Returns:
            {
                "action": "ne yapılacak",
                "deadline": "YYYY-MM-DD" or None,
                "time": "HH:MM" or None,
                "priority": "low/medium/high",
                "category": "work/personal/shopping/health/social",
                "related_people": ["isim1"],
                "recurrence": "once/daily/weekly" or None
            }
        """
        if not self.detect_task(text):
            return None
        
        task = {
            "action": self._extract_action(text),
            "deadline": self._extract_deadline(text),
            "time": self._extract_time(text),
            "priority": self._determine_priority(text),
            "category": self._determine_category(text),
            "related_people": self._extract_people(text),
            "recurrence": self._extract_recurrence(text),
            "original_text": text
        }
        
        # ID ve metadata ekle
        task["id"] = f"task_{int(time.time() * 1000)}"
        task["created_at"] = datetime.now().isoformat()
        task["status"] = "pending"
        task["reminders_sent"] = 0
        
        return task
    
    def _extract_action(self, text: str) -> str:
        """Ana eylemi çıkar"""
        # Basit temizlik: görev belirteçlerini kaldır
        action = text
        for indicator in self.task_indicators:
            action = action.replace(indicator, "")
        
        # Zaman ifadelerini kaldır
        for time_expr in self.time_patterns.keys():
            action = action.replace(time_expr, "")
        
        return action.strip()
    
    def _extract_deadline(self, text: str) -> Optional[str]:
        """Deadline çıkar"""
        text_lower = text.lower()
        
        for pattern, delta in self.time_patterns.items():
            if pattern in text_lower:
                deadline = datetime.now() + delta
                return deadline.strftime("%Y-%m-%d")
        
        # Tarih formatı ara (YYYY-MM-DD, DD/MM, DD.MM)
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}[./]\d{1,2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_time(self, text: str) -> Optional[str]:
        """Saat çıkar (HH:MM)"""
        time_pattern = r'(\d{1,2})[:\.](\d{2})'
        match = re.search(time_pattern, text)
        
        if match:
            hour, minute = match.groups()
            return f"{int(hour):02d}:{minute}"
        
        # "saat 3", "3'te" gibi ifadeler
        hour_pattern = r"saat\s*(\d{1,2})|(\d{1,2})['][td]e"
        match = re.search(hour_pattern, text.lower())
        if match:
            hour = match.group(1) or match.group(2)
            return f"{int(hour):02d}:00"
        
        return None
    
    def _determine_priority(self, text: str) -> str:
        """Öncelik belirle"""
        text_lower = text.lower()
        
        for priority, keywords in self.urgency_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return priority
        
        return "medium"
    
    def _determine_category(self, text: str) -> str:
        """Kategori belirle"""
        text_lower = text.lower()
        
        for category, keywords in self.category_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return category
        
        return "personal"
    
    def _extract_people(self, text: str) -> List[str]:
        """İlgili kişileri çıkar"""
        # Basit: büyük harfle başlayan kelimeleri al (isim olabilir)
        words = text.split()
        people = []
        
        for word in words:
            # Türkçe isim pattern: büyük harfle başlar, a-z/ş/ı/ğ/ü/ö içerir
            if word and word[0].isupper() and len(word) > 2:
                # Yaygın olmayan kelimeler
                if word.lower() not in ['ve', 'ile', 'için', 'bir', 'bu', 'şu']:
                    people.append(word.rstrip("'ya").rstrip("'ye").rstrip("'a").rstrip("'e"))
        
        return people
    
    def _extract_recurrence(self, text: str) -> Optional[str]:
        """Tekrarlama çıkar"""
        text_lower = text.lower()
        
        if any(w in text_lower for w in ["her gün", "günlük", "daily", "everyday"]):
            return "daily"
        elif any(w in text_lower for w in ["her hafta", "haftalık", "weekly"]):
            return "weekly"
        elif any(w in text_lower for w in ["her ay", "aylık", "monthly"]):
            return "monthly"
        
        return "once"


# ========================================
# TASK DATABASE
# ========================================

class TaskDatabase:
    """
    Görevleri sakla ve yönet
    """
    
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path("atom_workspace/tasks/tasks.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.tasks = {
            "active": [],      # Aktif görevler (bugün veya geçmiş)
            "pending": [],     # Bekleyen görevler (gelecek)
            "completed": [],   # Tamamlanmış
            "archived": []     # Arşivlenmiş
        }
        
        self._load_from_disk()
    
    def _load_from_disk(self):
        """Görevleri diskten yükle"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.tasks = json.load(f)
            except Exception:
                pass
    
    def _save_to_disk(self):
        """Görevleri diske kaydet"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[TaskDatabase] Kayıt hatası: {e}")
    
    def add_task(self, task: Dict) -> str:
        """Yeni görev ekle"""
        # Deadline kontrolü
        if task.get("deadline"):
            try:
                deadline = datetime.fromisoformat(task["deadline"])
                if deadline.date() <= datetime.now().date():
                    status = "active"
                else:
                    status = "pending"
            except:
                status = "active"
        else:
            status = "active"
        
        task["status"] = status
        self.tasks[status].append(task)
        self._save_to_disk()
        
        return task["id"]
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Görev getir"""
        for status, tasks in self.tasks.items():
            for task in tasks:
                if task["id"] == task_id:
                    return task
        return None
    
    def update_task(self, task_id: str, updates: Dict) -> bool:
        """Görev güncelle"""
        task = self.get_task(task_id)
        if task:
            task.update(updates)
            self._save_to_disk()
            return True
        return False
    
    def complete_task(self, task_id: str) -> bool:
        """Görevi tamamla"""
        for status, tasks in self.tasks.items():
            for i, task in enumerate(tasks):
                if task["id"] == task_id:
                    task["status"] = "completed"
                    task["completed_at"] = datetime.now().isoformat()
                    
                    # Completed'a taşı
                    self.tasks["completed"].append(task)
                    tasks.pop(i)
                    
                    self._save_to_disk()
                    return True
        return False
    
    def delete_task(self, task_id: str) -> bool:
        """Görevi sil"""
        for status, tasks in self.tasks.items():
            for i, task in enumerate(tasks):
                if task["id"] == task_id:
                    tasks.pop(i)
                    self._save_to_disk()
                    return True
        return False
    
    def get_active_tasks(self) -> List[Dict]:
        """Aktif görevleri getir"""
        return self.tasks["active"]
    
    def get_pending_tasks(self) -> List[Dict]:
        """Bekleyen görevleri getir"""
        return self.tasks["pending"]
    
    def get_today_tasks(self) -> List[Dict]:
        """Bugünkü görevleri getir"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        tasks = []
        for task in self.tasks["active"] + self.tasks["pending"]:
            if task.get("deadline") == today:
                tasks.append(task)
        
        return tasks
    
    def get_overdue_tasks(self) -> List[Dict]:
        """Gecikmiş görevleri getir"""
        today = datetime.now().date()
        overdue = []
        
        for task in self.tasks["active"]:
            if task.get("deadline"):
                try:
                    deadline = datetime.fromisoformat(task["deadline"]).date()
                    if deadline < today:
                        overdue.append(task)
                except:
                    pass
        
        return overdue
    
    def move_pending_to_active(self):
        """Zamanı gelen pending görevleri active'e taşı"""
        today = datetime.now().date()
        to_move = []
        
        for i, task in enumerate(self.tasks["pending"]):
            if task.get("deadline"):
                try:
                    deadline = datetime.fromisoformat(task["deadline"]).date()
                    if deadline <= today:
                        to_move.append(i)
                except:
                    pass
        
        # Ters sırayla taşı (index kayması önlemek için)
        for i in reversed(to_move):
            task = self.tasks["pending"].pop(i)
            task["status"] = "active"
            self.tasks["active"].append(task)
        
        if to_move:
            self._save_to_disk()
        
        return len(to_move)
    
    def get_all_tasks(self) -> Dict:
        """Tüm görevleri getir"""
        return self.tasks.copy()
    
    def get_statistics(self) -> Dict:
        """Görev istatistikleri"""
        return {
            "active": len(self.tasks["active"]),
            "pending": len(self.tasks["pending"]),
            "completed": len(self.tasks["completed"]),
            "archived": len(self.tasks["archived"]),
            "today": len(self.get_today_tasks()),
            "overdue": len(self.get_overdue_tasks())
        }


# ========================================
# TASK SCHEDULER
# ========================================

class TaskScheduler:
    """
    Zamanlayıcı ve hatırlatıcılar
    """
    
    def __init__(self, database: TaskDatabase, notification_callback: Callable = None):
        self.db = database
        self.notify = notification_callback or self._default_notify
        self._running = False
        self._check_interval = 60  # 1 dakika
    
    def _default_notify(self, message: str, task: Dict = None):
        """Varsayılan bildirim (print)"""
        print(f"[TaskScheduler] 📋 {message}")
    
    async def start(self):
        """Zamanlayıcıyı başlat"""
        self._running = True
        print("[TaskScheduler] Başlatıldı")
        
        while self._running:
            await self._check_tasks()
            await asyncio.sleep(self._check_interval)
    
    def stop(self):
        """Zamanlayıcıyı durdur"""
        self._running = False
        print("[TaskScheduler] Durduruldu")
    
    async def _check_tasks(self):
        """Görevleri kontrol et ve hatırlatma yap"""
        # Pending → Active taşı
        moved = self.db.move_pending_to_active()
        if moved > 0:
            print(f"[TaskScheduler] {moved} görev aktif hale getirildi")
        
        # Bugünün görevleri
        today_tasks = self.db.get_today_tasks()
        for task in today_tasks:
            # Henüz hatırlatma yapılmadıysa
            if task.get("reminders_sent", 0) == 0:
                self.notify(
                    f"Bugün yapman gereken: {task.get('action', 'Görev')}",
                    task
                )
                task["reminders_sent"] = 1
                self.db.update_task(task["id"], {"reminders_sent": 1})
        
        # Gecikmiş görevler
        overdue = self.db.get_overdue_tasks()
        for task in overdue:
            if task.get("reminders_sent", 0) < 3:  # Max 3 hatırlatma
                self.notify(
                    f"⚠️ Gecikmiş görev: {task.get('action', 'Görev')} ({task.get('deadline')})",
                    task
                )
                task["reminders_sent"] = task.get("reminders_sent", 0) + 1
                self.db.update_task(task["id"], {"reminders_sent": task["reminders_sent"]})
    
    def get_next_reminder_time(self, task: Dict) -> Optional[datetime]:
        """Görevin bir sonraki hatırlatma zamanı"""
        if not task.get("deadline"):
            return None
        
        try:
            deadline = datetime.fromisoformat(task["deadline"])
            
            # Deadline günü sabah 9
            if task.get("time"):
                hour, minute = map(int, task["time"].split(":"))
                return deadline.replace(hour=hour, minute=minute)
            else:
                return deadline.replace(hour=9, minute=0)
        except:
            return None


# ========================================
# AUTONOMOUS TASK MANAGER
# ========================================

class AutonomousTaskManager:
    """
    Ana görev yönetim sistemi
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls) -> 'AutonomousTaskManager':
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self, notification_callback: Callable = None):
        self.nlu = TaskNLU()
        self.db = TaskDatabase()
        self.scheduler = TaskScheduler(self.db, notification_callback)
    
    def process_message(self, text: str) -> Optional[Dict]:
        """
        Mesajı işle ve görev varsa ekle
        
        Returns:
            Eklenen görev veya None
        """
        task = self.nlu.extract_task(text)
        
        if task:
            self.db.add_task(task)
            return task
        
        return None
    
    def add_task_manual(
        self,
        action: str,
        deadline: str = None,
        priority: str = "medium",
        category: str = "personal",
        related_people: List[str] = None
    ) -> Dict:
        """Manuel görev ekleme"""
        task = {
            "id": f"task_{int(time.time() * 1000)}",
            "action": action,
            "deadline": deadline,
            "priority": priority,
            "category": category,
            "related_people": related_people or [],
            "recurrence": "once",
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "reminders_sent": 0
        }
        
        self.db.add_task(task)
        return task
    
    def complete_task(self, task_id: str) -> bool:
        """Görevi tamamla"""
        return self.db.complete_task(task_id)
    
    def delete_task(self, task_id: str) -> bool:
        """Görevi sil"""
        return self.db.delete_task(task_id)
    
    def get_summary(self) -> Dict:
        """Günlük özet"""
        stats = self.db.get_statistics()
        today = self.db.get_today_tasks()
        overdue = self.db.get_overdue_tasks()
        
        return {
            "statistics": stats,
            "today_tasks": today,
            "overdue_tasks": overdue,
            "message": self._generate_summary_message(stats, today, overdue)
        }
    
    def _generate_summary_message(
        self,
        stats: Dict,
        today: List[Dict],
        overdue: List[Dict]
    ) -> str:
        """Özet mesajı oluştur"""
        parts = []
        
        if overdue:
            parts.append(f"⚠️ {len(overdue)} gecikmiş görev var!")
        
        if today:
            tasks_str = ", ".join(t.get("action", "?")[:30] for t in today[:3])
            parts.append(f"📋 Bugün: {tasks_str}")
        
        if stats["pending"] > 0:
            parts.append(f"⏳ {stats['pending']} bekleyen görev")
        
        if not parts:
            parts.append("✅ Tüm görevler tamam!")
        
        return " | ".join(parts)
    
    async def start_scheduler(self):
        """Zamanlayıcıyı başlat"""
        await self.scheduler.start()


# ========================================
# TOOL FUNCTIONS
# ========================================

# Global instance
_task_manager = None

def get_task_manager() -> AutonomousTaskManager:
    """Global task manager instance"""
    global _task_manager
    if _task_manager is None:
        _task_manager = AutonomousTaskManager()
    return _task_manager


def add_task(
    action: str,
    deadline: str = None,
    priority: str = "medium",
    category: str = "personal",
    related_people: List[str] = None
) -> Dict:
    """
    Yeni görev ekle
    
    Args:
        action: "Ela'ya hediye al"
        deadline: "2024-12-29" veya None
        priority: "low/medium/high"
        category: "work/personal/shopping/health/social"
        related_people: ["Ela"]
    
    Returns:
        Eklenen görev
    """
    try:
        manager = get_task_manager()
        task = manager.add_task_manual(
            action=action,
            deadline=deadline,
            priority=priority,
            category=category,
            related_people=related_people
        )
        return {"status": "success", "task": task}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def complete_task(task_id: str) -> Dict:
    """Görevi tamamla"""
    try:
        manager = get_task_manager()
        success = manager.complete_task(task_id)
        
        if success:
            return {"status": "success", "message": f"Görev tamamlandı: {task_id}"}
        else:
            return {"status": "not_found", "message": f"Görev bulunamadı: {task_id}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def delete_task(task_id: str) -> Dict:
    """Görevi sil"""
    try:
        manager = get_task_manager()
        success = manager.delete_task(task_id)
        
        if success:
            return {"status": "success", "message": f"Görev silindi: {task_id}"}
        else:
            return {"status": "not_found", "message": f"Görev bulunamadı: {task_id}"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def list_tasks(filter_type: str = "all") -> Dict:
    """
    Görevleri listele
    
    Args:
        filter_type: "all/active/pending/completed/today/overdue"
    """
    try:
        manager = get_task_manager()
        
        if filter_type == "all":
            tasks = manager.db.get_all_tasks()
        elif filter_type == "active":
            tasks = manager.db.get_active_tasks()
        elif filter_type == "pending":
            tasks = manager.db.get_pending_tasks()
        elif filter_type == "completed":
            tasks = manager.db.tasks["completed"]
        elif filter_type == "today":
            tasks = manager.db.get_today_tasks()
        elif filter_type == "overdue":
            tasks = manager.db.get_overdue_tasks()
        else:
            tasks = manager.db.get_all_tasks()
        
        return {"status": "success", "tasks": tasks, "filter": filter_type}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_task_summary() -> Dict:
    """Görev özeti al"""
    try:
        manager = get_task_manager()
        return manager.get_summary()
    except Exception as e:
        return {"error": str(e)}


def process_task_from_text(text: str) -> Dict:
    """
    Doğal dilden görev çıkar ve ekle
    
    Args:
        text: "Yarın Ela'ya hediye almam lazım"
    
    Returns:
        Eklenen görev veya hata
    """
    try:
        manager = get_task_manager()
        task = manager.process_message(text)
        
        if task:
            return {
                "status": "success",
                "task": task,
                "message": f"Görev eklendi: {task.get('action')}"
            }
        else:
            return {
                "status": "no_task",
                "message": "Bu cümlede görev tespit edilemedi"
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ========================================
# TEST
# ========================================

if __name__ == "__main__":
    print("=== Autonomous Task Manager Test ===\n")
    
    manager = get_task_manager()
    
    # Test 1: Doğal dilden görev çıkarma
    print("1. Doğal dilden görev çıkarma...")
    texts = [
        "Yarın Ela'ya hediye almam lazım",
        "Bugün saat 3'te toplantı var",
        "Gelecek hafta doktora git",
        "Acil! Proje teslimi bugün!"
    ]
    
    for text in texts:
        task = manager.nlu.extract_task(text)
        if task:
            print(f"   ✅ '{text[:30]}...'")
            print(f"      → Action: {task['action']}")
            print(f"      → Deadline: {task.get('deadline')}")
            print(f"      → Priority: {task['priority']}")
            print(f"      → Category: {task['category']}")
    
    # Test 2: Görev ekleme
    print("\n2. Manuel görev ekleme...")
    result = add_task(
        action="Test görevi",
        deadline="2024-12-30",
        priority="high"
    )
    print(f"   Sonuç: {result}")
    
    # Test 3: Görev listesi
    print("\n3. Görev listesi...")
    tasks = list_tasks("all")
    print(f"   Toplam görevler: {tasks}")
    
    # Test 4: Özet
    print("\n4. Günlük özet...")
    summary = get_task_summary()
    print(f"   {summary.get('message', 'Özet yok')}")
    
    print("\n✅ Test tamamlandı!")
