"""
Offline Tools - Yerel araçlar (İnternet gerektirmez)
"""
import os
import json
import datetime
import subprocess
import logging
import re
import logging
from pathlib import Path

logger = logging.getLogger("atomik.tools.offline")

class OfflineTools:
    """Offline modda kullanılabilecek yerel araçlar"""
    
    def __init__(self):
        self.home_dir = Path.home()
        self.atomik_dir = self.home_dir / ".atomik"
        self.reminders_file = self.atomik_dir / "reminders.json"
        
        # Workspace directory (where files are created)
        # Assuming run from project root
        self.workspace_dir = Path.cwd() / "atom_workspace"
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Legacy notes dir (backup)
        self.notes_dir = self.atomik_dir / "notes"
        self.atomik_dir.mkdir(exist_ok=True)
        self.notes_dir.mkdir(exist_ok=True)
        
        # Load reminders
        self.reminders = self._load_reminders()
    
    # === FILE OPERATIONS ===
    
    def create_file(self, filename: str, content: str = "") -> str:
        """Dosya oluştur - atom_workspace içinde"""
        try:
            if "/" in filename or "\\" in filename:
                filepath = Path(filename).expanduser()
            else:
                filepath = self.workspace_dir / filename
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            return f"Dosya oluşturuldu: {filepath}\n(İçerik: '{content[:100]}{'...' if len(content) > 100 else ''}')"
        except Exception as e:
            return f"Dosya oluşturma hatası: {e}"
    
    def smart_create_file(self, description: str, content: str = "") -> str:
        """LLM ile akıllı dosya adı ve içerik oluştur"""
        try:
            from core.offline.llm_client import OllamaClient
            client = OllamaClient()
            
            # Step 1: Generate filename
            filename_prompt = f"""Aşağıdaki açıklama için uygun bir dosya adı öner.
Sadece dosya adını yaz, uzantı dahil (.txt, .md, .py vb).
Kod istekleri için .py, metin için .txt kullan.
Türkçe karakter kullanma. Boşluk yerine alt çizgi kullan.
Maksimum 20 karakter.

Açıklama: {description[:200]}

Dosya adı:"""
            
            filename = client.generate_text(filename_prompt).strip()
            
            # Clean filename
            import re
            filename = re.sub(r'[^\w\.\-]', '_', filename)
            filename = filename.strip('_').strip()
            if not filename or len(filename) < 3:
                filename = f"belge_{datetime.datetime.now().strftime('%H%M%S')}.txt"
            if '.' not in filename:
                # Guess extension from description
                if any(kw in description.lower() for kw in ['python', 'kod', 'oyun', 'script', 'programı']):
                    filename += '.py'
                else:
                    filename += '.txt'
            
            # Step 2: Generate content if empty
            if not content:
                ext = filename.split('.')[-1].lower() if '.' in filename else 'txt'
                
                if ext == 'py':
                    content_prompt = f"""Aşağıdaki açıklamaya uygun Python kodu yaz.
Sadece çalışır Python kodu yaz, açıklama yapma.
Gerekli importları ekle.

Açıklama: {description}

Python kodu:
```python"""
                    raw_content = client.generate_text(content_prompt)
                    # Extract code from markdown if present
                    code_match = re.search(r'```python\s*(.*?)```', raw_content, re.DOTALL)
                    if code_match:
                        content = code_match.group(1).strip()
                    else:
                        # Remove markdown if any
                        content = raw_content.replace('```python', '').replace('```', '').strip()
                
                elif ext in ['js', 'html', 'css']:
                    content_prompt = f"""Aşağıdaki açıklamaya uygun {ext.upper()} kodu yaz.
Sadece çalışır kod yaz.

Açıklama: {description}

Kod:"""
                    content = client.generate_text(content_prompt).strip()
                
                else:
                    # Text file - generate text content
                    content_prompt = f"""Aşağıdaki konuda kısa bir metin yaz:

Konu: {description}

Metin:"""
                    content = client.generate_text(content_prompt).strip()
            
            # Create file
            filepath = self.workspace_dir / filename
            filepath.write_text(content, encoding="utf-8")
            
            preview = content[:150].replace('\n', ' ')
            return f"✅ Dosya oluşturuldu: {filepath.name}\n📝 İçerik ({len(content)} karakter): '{preview}...'"
            
        except Exception as e:
            # Fallback to generic name
            filename = f"belge_{datetime.datetime.now().strftime('%H%M%S')}.txt"
            filepath = self.workspace_dir / filename
            filepath.write_text(content or description, encoding="utf-8")
            return f"Dosya oluşturuldu (fallback): {filepath.name} - Hata: {e}"
    
    def append_to_file(self, filename: str, content: str) -> str:
        """Dosyaya içerik ekle"""
        try:
            if "/" in filename or "\\" in filename:
                filepath = Path(filename).expanduser()
            else:
                filepath = self.workspace_dir / filename
            
            if not filepath.exists():
                return f"Dosya bulunamadı: {filename}"
            
            with open(filepath, 'a', encoding='utf-8') as f:
                f.write('\n' + content)
            
            return f"'{filename}' dosyasına eklendi:\n{content[:100]}{'...' if len(content) > 100 else ''}"
        except Exception as e:
            return f"Dosya ekleme hatası: {e}"
    
    def edit_file(self, filename: str, old_text: str, new_text: str) -> str:
        """Dosyada metin değiştir"""
        try:
            if "/" in filename or "\\" in filename:
                filepath = Path(filename).expanduser()
            else:
                filepath = self.workspace_dir / filename
            
            if not filepath.exists():
                return f"Dosya bulunamadı: {filename}"
            
            content = filepath.read_text(encoding='utf-8')
            
            if old_text not in content:
                return f"'{old_text}' metni dosyada bulunamadı."
            
            new_content = content.replace(old_text, new_text, 1)
            filepath.write_text(new_content, encoding='utf-8')
            
            return f"'{filename}' dosyası düzenlendi:\n'{old_text[:30]}...' → '{new_text[:30]}...'"
        except Exception as e:
            return f"Dosya düzenleme hatası: {e}"
    
    def get_last_file(self) -> str:
        """Son oluşturulan dosyanın adını döndür"""
        try:
            files = list(self.workspace_dir.glob('*'))
            if not files:
                return None
            # Sort by modification time
            files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
            return str(files[0])
        except:
            return None
    
    def read_file(self, filename: str) -> str:
        """Dosya oku - atom_workspace içinde"""
        try:
            if "/" in filename or "\\" in filename:
                filepath = Path(filename).expanduser()
            else:
                # Try workspace first
                filepath = self.workspace_dir / filename
                if not filepath.exists():
                    # Fallback to notes dir
                    filepath = self.notes_dir / filename
            
            if not filepath.exists():
                return f"Dosya bulunamadı: {filename}"
            
            content = filepath.read_text(encoding="utf-8")
            return f"📄 {filepath.name} içeriği:\n{content}"
        except Exception as e:
            return f"Dosya okuma hatası: {e}"
    
    def list_files(self, directory: str = None) -> str:
        """Dosyaları listele"""
        try:
            if directory:
                path = Path(directory).expanduser()
            else:
                path = self.workspace_dir
            
            if not path.exists():
                return f"Dizin bulunamadı: {path}"
            
            files = list(path.iterdir())
            if not files:
                return f"{path.name} dizini boş."
            
            result = f"📁 {path.name} içeriği:\n"
            for f in files[:20]:  # Max 20
                icon = "📄" if f.is_file() else "📁"
                result += f"{icon} {f.name}\n"
            return result
        except Exception as e:
            return f"Listeleme hatası: {e}"
    
    # === REMINDER SYSTEM ===
    
    def _load_reminders(self) -> list:
        """Hatırlatıcıları yükle"""
        if self.reminders_file.exists():
            try:
                return json.loads(self.reminders_file.read_text())
            except:
                return []
        return []
    
    def _save_reminders(self):
        """Hatırlatıcıları kaydet"""
        self.reminders_file.write_text(json.dumps(self.reminders, ensure_ascii=False, indent=2))
    
    def add_reminder(self, text: str, time_str: str = None) -> str:
        """Hatırlatıcı ekle"""
        due_time = self.parse_smart_time(text)
        
        reminder = {
            "id": len(self.reminders) + 1,
            "text": text,
            "time": time_str or (due_time.strftime("%H:%M") if due_time else None),
            "due_timestamp": due_time.timestamp() if due_time else None,
            "created": datetime.datetime.now().isoformat(),
            "done": False
        }
        self.reminders.append(reminder)
        self._save_reminders()
        
        msg = f"Hatırlatıcı eklendi: {text}"
        if due_time:
            msg += f" (Zaman: {due_time.strftime('%H:%M:%S')})"
        return msg
    
    def list_reminders(self) -> str:
        """Hatırlatıcıları listele"""
        active = [r for r in self.reminders if not r.get("done", False)]
        if not active:
            return "Aktif hatırlatıcı yok."
        
        result = "Hatırlatıcılar:\n"
        for r in active:
            result += f"[{r['id']}] {r['text']}"
            if r.get('time'):
                result += f" ({r['time']})"
            result += "\n"
        return result
    
    def complete_reminder(self, reminder_id: int) -> str:
        """Hatırlatıcıyı tamamla"""
        for r in self.reminders:
            if r['id'] == reminder_id:
                r['done'] = True
                self._save_reminders()
                return f"Hatırlatıcı tamamlandı: {r['text']}"
        return "Hatırlatıcı bulunamadı."

    def parse_smart_time(self, text: str) -> datetime.datetime:
        """Metinden zaman çıkarımı yap"""
        now = datetime.datetime.now()
        # 5 dk sonra
        m = re.search(r'(\d+)\s*(dk|dakika|saat|sn|saniye)\s+sonra', text, re.IGNORECASE)
        if m:
            val = int(m.group(1))
            unit = m.group(2).lower()
            if "saat" in unit: delta = datetime.timedelta(hours=val)
            elif "sn" in unit or "saniye" in unit: delta = datetime.timedelta(seconds=val)
            else: delta = datetime.timedelta(minutes=val)
            return now + delta
            
        # Saat UU:DD
        m = re.search(r'saat\s*(\d{1,2})[:.](\d{2})', text, re.IGNORECASE)
        if m:
            h, minute = int(m.group(1)), int(m.group(2))
            target = now.replace(hour=h, minute=minute, second=0, microsecond=0)
            if target < now: target += datetime.timedelta(days=1)
            return target
            
        return None

    def check_due_reminders(self) -> list:
        """Vakti gelen hatırlatıcıları bul ve işaretle"""
        due = []
        now = datetime.datetime.now().timestamp()
        changed = False
        
        for r in self.reminders:
            if not r.get("done", False) and r.get("due_timestamp"):
                if now >= r["due_timestamp"]:
                    r["done"] = True # Mark as one-time alerted (or move to 'alerted' state?)
                    # For simplicty, mark done so it doesn't alert forever.
                    # Ideally we should have an 'acknowledged' state.
                    # But user asked for proactive notification.
                    due.append(r["text"])
                    changed = True
        
        if changed:
            self._save_reminders()
            
        return due
    
        return "Hatırlatıcı bulunamadı."

    # === CLIPBOARD ===
    
    def copy_to_clipboard(self, text: str) -> str:
        """Metni panoya kopyala"""
        try:
            # Try wl-copy (Wayland)
            subprocess.run(["wl-copy"], input=text.encode('utf-8'), check=True, timeout=1)
            return "Metin panoya kopyalandı (Wayland)."
        except:
            try:
                # Try xclip (X11)
                p = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
                p.communicate(input=text.encode('utf-8'))
                return "Metin panoya kopyalandı (X11)."
            except:
                return "Pano aracı bulunamadı (wl-copy veya xclip yükleyin)."

    # === COMPUTER USE (UI Control) ===
    
    def click_on_text(self, target_text: str, position_hint: str = None) -> str:
        """Ekranda metin bul ve tıkla (konum ipucu ile filtreleyebilir)"""
        try:
            from tools.vision import get_screen_analyzer
            analyzer = get_screen_analyzer()
            success, msg = analyzer.find_and_click(target_text, position_hint=position_hint)
            return msg
        except ImportError:
            return "Vision modülü yüklenemedi. pip install easyocr pyautogui opencv-python"
        except Exception as e:
            return f"Tıklama hatası: {e}"
    
    def smart_click(self, description: str) -> str:
        """Akıllı tıklama - renk + OCR + LLM + region fallback"""
        try:
            from tools.vision import get_screen_analyzer
            analyzer = get_screen_analyzer()
            # Use comprehensive_click which tries all methods
            success, msg = analyzer.comprehensive_click(description)
            return msg
        except ImportError:
            return "Vision modülü yüklenemedi."
        except Exception as e:
            return f"Akıllı tıklama hatası: {e}"
    
    def type_text_at(self, target_text: str, input_text: str) -> str:
        """Belirtilen alanın yanına metin yaz"""
        try:
            from tools.vision import get_screen_analyzer
            analyzer = get_screen_analyzer()
            success, msg = analyzer.find_and_type(target_text, input_text)
            return msg
        except ImportError:
            return "Vision modülü yüklenemedi."
        except Exception as e:
            return f"Yazma hatası: {e}"
    
    def open_application(self, app_name: str) -> str:
        """Uygulamayı aç (Ctrl+Space ile arar)"""
        try:
            from tools.vision import get_screen_analyzer
            analyzer = get_screen_analyzer()
            success, msg = analyzer.open_application(app_name)
            return msg
        except ImportError:
            return "Vision modülü yüklenemedi."
        except Exception as e:
            return f"Uygulama açma hatası: {e}"
    
    def read_screen_text(self) -> str:
        """Ekrandaki tüm yazıları oku"""
        try:
            from tools.vision import get_screen_analyzer
            analyzer = get_screen_analyzer()
            text = analyzer.read_screen()
            return f"Ekranda okunan yazılar:\n{text[:500]}{'...' if len(text) > 500 else ''}"
        except ImportError:
            return "Vision modülü yüklenemedi."
        except Exception as e:
            return f"Okuma hatası: {e}"
    
    def press_hotkey(self, keys: str) -> str:
        """Klavye kısayolu bas (örn: 'ctrl+c', 'alt+f4')"""
        try:
            from tools.vision import get_action_executor
            executor = get_action_executor()
            key_list = [k.strip() for k in keys.split('+')]
            executor.hotkey(*key_list)
            return f"Kısayol basıldı: {keys}"
        except ImportError:
            return "Vision modülü yüklenemedi."
        except Exception as e:
            return f"Kısayol hatası: {e}"

    # === SYSTEM COMMANDS ===
    
    def run_command(self, command: str) -> str:
        """Sistem komutu çalıştır (güvenli)"""
        # Whitelist of safe commands
        safe_commands = ["ls", "pwd", "date", "whoami", "df", "free", "uptime", "cat", "head", "tail", "wc"]
        
        cmd_parts = command.split()
        if not cmd_parts:
            return "Boş komut."
        
        base_cmd = cmd_parts[0]
        if base_cmd not in safe_commands:
            return f"Güvenlik: '{base_cmd}' komutu izin verilmiyor."
        
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, 
                text=True, timeout=10
            )
            output = result.stdout or result.stderr
            return output[:500] if output else "Komut çalıştırıldı (çıktı yok)."
        except subprocess.TimeoutExpired:
            return "Komut zaman aşımına uğradı."
        except Exception as e:
            return f"Hata: {e}"
    
    def get_datetime(self) -> str:
        """Tarih ve saat"""
        now = datetime.datetime.now()
        return now.strftime("%d %B %Y %A, %H:%M:%S")
    
    # === NOTE TAKING ===
    
    def add_note(self, title: str, content: str) -> str:
        """Not ekle"""
        filename = f"{title.replace(' ', '_')}.txt"
        return self.create_file(filename, content)
    
    def search_notes(self, query: str) -> str:
        """Notlarda ara"""
        results = []
        for note_file in self.notes_dir.glob("*.txt"):
            try:
                content = note_file.read_text()
                if query.lower() in content.lower() or query.lower() in note_file.stem.lower():
                    results.append(note_file.stem)
            except:
                continue
        
        if not results:
            return f"'{query}' bulunamadı."
        
        return f"Bulunan notlar: {', '.join(results)}"


# Tool dispatcher - matches user intent to tool
def get_tool_response(user_text: str, tools: OfflineTools) -> tuple:
    """
    Kullanıcı metnini analiz et ve uygun aracı çağır.
    Returns: (tool_used: bool, response: str)
    """
    text_lower = user_text.lower()
    
    # --- FILE CREATION ---
    # Keywords for creation actions
    creation_keywords = ["oluştur", "yarat", "yaz", "kaydet", "ekle", "hakkında", "konulu", "başlıklı", 
                         "yap", "kodla", "programla", "geliştir"]
    # Keywords for file types (including code projects)
    file_keywords = ["dosya", "belge", "not", "metin", "oyun", "program", "script", "kod", "uygulama", "proje"]
    
    # Check for implicit creation: "yeni bir metin belgesine X hakkında yaz"
    # Also: "belgesine" (dative form implies creating into something)
    implicit_creation = any(w in text_lower for w in ["yeni bir", "belgesine", "dosyasına", "notuna"])
    
    if (any(k in text_lower for k in creation_keywords) and any(f in text_lower for f in file_keywords)) or \
       (implicit_creation and any(f in text_lower for f in file_keywords)):
        # 1. Dosya adını bul
        filename = None
        # Regex for filenames with extension (test.txt, data.json)
        ext_match = re.search(r'\b[\w\-\.]+\.(txt|py|md|json|html|css|js|log)\b', user_text, re.IGNORECASE)
        if ext_match:
            filename = ext_match.group(0)
        else:
            # "adı deneme olsun"
            name_match = re.search(r'(?:adı|ismi)\s+([\w\-\.]+)', user_text, re.IGNORECASE)
            if name_match:
                filename = name_match.group(1)
                if "." not in filename: 
                    filename += ".txt"
        
        # 2. İçeriği veya konuyu bul
        content = ""
        topic = ""
        
        # "X hakkında" pattern - X is the topic
        topic_match = re.search(r'(.+?)\s+hakkında', user_text, re.IGNORECASE)
        if topic_match:
            topic = topic_match.group(1).strip()
            # Clean up: remove "yeni bir metin belgesine" etc
            for remove in ["yeni bir metin belgesine", "yeni bir dosyaya", "yeni bir notuna", "belgesine"]:
                topic = topic.replace(remove, "").strip()
        
        # Direct content patterns
        content_patterns = [
            r'(?:içinde|içeriği)\s+(.+?)\s+(?:yazan|olan|bulunan)',
            r'(?:yaz|ekle)[:\s]+(.+)',
            r'(?:içerik|metin)\s*:\s*(.+)',
            r'şunu yaz[\s:]+(.+)',
            r'(\S.+?)\s+(?:diyen|yazan|içeren)\s+(?:bir\s+)?(?:dosya|belge|metin)'
        ]
        
        for pat in content_patterns:
            m = re.search(pat, user_text, re.IGNORECASE | re.DOTALL)
            if m:
                content = m.group(1).strip()
                break
        
        # If no content but we have topic, create placeholder content
        if not content and topic:
            content = f"{topic.capitalize()} hakkında oluşturulan belge."
        
        # If no filename, use smart_create_file with topic/description
        if not filename:
            # Check if this is a code request (oyun, program, kod, script)
            code_keywords = ['oyun', 'program', 'kod', 'script', 'uygulama', 'python', 'pygame']
            is_code_request = any(kw in text_lower for kw in code_keywords)
            
            if is_code_request or topic:
                # Use LLM to generate filename AND content
                return True, tools.smart_create_file(topic or user_text, content)
            else:
                # Fallback with timestamp for simple text files
                ts = datetime.datetime.now().strftime("%H%M%S")
                filename = f"belge_{ts}.txt"
            
        if filename:
            return True, tools.create_file(filename, content)
            
    # --- FILE READING ---
    if "oku" in text_lower or "göster" in text_lower or "aç" in text_lower:
        # Regex for filename
        ext_match = re.search(r'\b[\w\-\.]+\.(txt|py|md|json|html|css|js|log)\b', user_text, re.IGNORECASE)
        if ext_match:
            return True, tools.read_file(ext_match.group(0))
            
    # --- LIST FILES ---
    if any(kw in text_lower for kw in ["dosyaları listele", "dosyalar ne", "hangi dosyalar", "klasör içeriği"]):
        return True, tools.list_files()
    
    # --- REMINDERS ---
    if "hatırlat" in text_lower or "alarm" in text_lower:
        # "bana su içmeyi hatırlat", "yarın toplantı var hatırlat"
        # Extract meaningful part
        text = user_text
        for rem_kw in ["hatırlat", "hatırlatıcı", "bana", "lütfen", "ekle", "kur"]:
            text = re.sub(f"\\b{rem_kw}\\b", "", text, flags=re.IGNORECASE)
        
        text = text.strip()
        if text:
            return True, tools.add_reminder(text)
        else:
             return True, "Ne hatırlatayım?"
             
    if "hatırlatıcılar" in text_lower or "alarmlar" in text_lower:
        return True, tools.list_reminders()

    # --- SYSTEM ---
    if any(kw in text_lower for kw in ["saat kaç", "tarih", "bugün ne"]):
        return True, tools.get_datetime()
        
    # --- NOTES ---
    if "not al" in text_lower or "not et" in text_lower:
        # "şunu not al: ..."
        content_match = re.search(r'(?:not al|not et)[:\s]+(.*)', user_text, re.IGNORECASE)
        if content_match:
            content = content_match.group(1)
            title = f"not_{datetime.datetime.now().strftime('%H%M')}"
            return True, tools.add_note(title, content)
    
    # --- COMPUTER USE (UI Control) ---
    # "Dosyalar'a tıkla", "Terminal aç", "mavi butona tıkla"
    
    # Extract position hint from user text (sağ alt, sol üst, etc.)
    position_hint = None
    position_keywords = ["sağ", "sol", "üst", "alt", "altta", "üstte", "ortada", "aşağı", "yukarı"]
    for kw in position_keywords:
        if kw in text_lower:
            if position_hint:
                position_hint += " " + kw
            else:
                position_hint = kw
    
    # Check for color keywords -> use smart_click (LLM + Color + OCR)
    color_keywords = ["mavi", "kırmızı", "yeşil", "gri", "blue", "red", "green", "gray"]
    has_color = any(c in text_lower for c in color_keywords)
    
    if has_color and ("tıkla" in text_lower or "bas" in text_lower):
        # Route to smart_click for intelligent detection
        return True, tools.smart_click(user_text)
    
    # Extract text from "üstünde X yazıyor" format first
    label_match = re.search(r'üstünde\s+["\']?(.+?)["\']?\s+yazıyor', user_text, re.IGNORECASE)
    if label_match and ("tıkla" in text_lower or "bas" in text_lower):
        target = label_match.group(1).strip()
        if target:
            return True, tools.click_on_text(target, position_hint=position_hint)
    
    # Click on text patterns
    click_patterns = [
        r"(?:tıkla|bas|seç)\s+(?:üzerine\s+)?['\"]?(.+?)['\"]?\s*$",
        r"['\"]?(.+?)['\"]?\s+(?:üzerine|butonuna?|yazısına|\'?[ea]\s+)?\s*(?:tıkla|bas)",
        r"(.+?)\s+aç\s*$",  # "terminal aç"
        r"(.+?)\s+butona?\s+tıkla",  # "mavi butona tıkla"
    ]
    
    for pat in click_patterns:
        m = re.search(pat, user_text, re.IGNORECASE)
        if m:
            # Use smart_click for comprehensive handling (color + OCR + region fallback)
            return True, tools.smart_click(user_text)
    
    # Open application
    if any(kw in text_lower for kw in ["aç", "başlat", "çalıştır"]):
        app_match = re.search(r'(.+?)\s+(?:uygulamasını\s+)?(?:aç|başlat|çalıştır)', user_text, re.IGNORECASE)
        if app_match:
            app_name = app_match.group(1).strip()
            if app_name:
                return True, tools.open_application(app_name)
    
    # Type text
    type_match = re.search(r'(?:yaz|gir)[:\s]+["\']?(.+?)["\']?\s*$', user_text, re.IGNORECASE)
    if type_match:
        text_to_type = type_match.group(1)
        if text_to_type:
            try:
                from tools.vision import get_action_executor
                executor = get_action_executor()
                executor.type_text(text_to_type)
                return True, f"Yazıldı: {text_to_type}"
            except Exception as e:
                return True, f"Yazma hatası: {e}"
    
    # Hotkey
    hotkey_match = re.search(r'(?:kısayol|tuş|bas)[:\s]+(.+)', user_text, re.IGNORECASE)
    if hotkey_match:
        keys = hotkey_match.group(1).strip()
        return True, tools.press_hotkey(keys)
    
    # Read screen text (OCR)
    if any(kw in text_lower for kw in ["ekranı oku", "yazıları oku", "ocr"]):
        return True, tools.read_screen_text()
    
    # --- LLM-BASED INTENT CLASSIFICATION (FALLBACK) ---
    # If no regex patterns matched, use LLM to understand intent
    try:
        from core.offline.intent import classify_intent
        
        result = classify_intent(user_text)
        tool_name = result.get("tool")
        params = result.get("params", {})
        
        if tool_name:
            logger.info(f"LLM classified intent: {tool_name} with params: {params}")
            
            # Route to appropriate tool based on LLM classification
            if tool_name == "dosya_olustur":
                filename = params.get("filename")
                content = params.get("content", "")
                topic = params.get("topic", "")
                
                if filename:
                    return True, tools.create_file(filename, content)
                elif topic:
                    return True, tools.smart_create_file(topic, content or f"{topic} hakkında belge.")
                else:
                    return True, tools.smart_create_file(user_text, content)
            
            elif tool_name == "dosya_oku":
                filename = params.get("filename") or params.get("target")
                if filename:
                    return True, tools.read_file(filename)
            
            elif tool_name == "dosya_duzenle":
                filename = params.get("filename")
                if filename:
                    return True, tools.read_file(filename)  # Show content first
            
            elif tool_name == "dosya_ekle":
                filename = params.get("filename")
                content = params.get("content", "")
                if filename and content:
                    return True, tools.append_to_file(filename, content)
            
            elif tool_name == "dosya_listele":
                return True, tools.list_files()
            
            elif tool_name == "uygulama_ac":
                target = params.get("target")
                if target:
                    return True, tools.open_application(target)
            
            elif tool_name == "tikla":
                target = params.get("target", "")
                position = params.get("position", "")
                color = params.get("color", "")
                description = f"{position} {color} {target}".strip()
                if description:
                    return True, tools.smart_click(description or user_text)
            
            elif tool_name == "hatirlatici":
                content = params.get("content") or params.get("topic")
                if content:
                    return True, tools.add_reminder(content)
                else:
                    return True, tools.list_reminders()
            
            elif tool_name == "tarih_saat":
                return True, tools.get_datetime()
            
            elif tool_name == "sistem_bilgisi":
                return True, tools.get_system_info()
            
            # sohbet -> return False, let LLM handle it
            
    except ImportError:
        logger.debug("Intent classifier not available")
    except Exception as e:
        logger.warning(f"LLM intent classification failed: {e}")
            
    return False, None
