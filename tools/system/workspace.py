"""
Atomik Virtual Workspace Manager
Sanal ekranda veya 2. masaüstünde uygulama kontrolü için Python wrapper.
"""
import subprocess
import os
import time
from typing import Optional, Tuple

class VirtualWorkspace:
    """Xvfb tabanlı sanal ekran ve workspace yöneticisi."""
    
    VIRTUAL_DISPLAY = ":99"
    VNC_PORT = 5900
    RESOLUTION = "1888x1041"
    TARGET_WORKSPACE = 1  # 2. masaüstü (0-indexed)
    
    _instance = None
    _is_running = False
    _captured_window_id = None  # Yakalanan pencere ID'si
    
    @classmethod
    def get_instance(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _run_cmd(self, cmd: list, env: dict = None, capture: bool = True) -> Tuple[int, str]:
        """Komut çalıştır."""
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            env=env or os.environ
        )
        return result.returncode, result.stdout.strip() if capture else ""
    
    def _get_virtual_env(self) -> dict:
        """Sanal ekran için environment."""
        env = os.environ.copy()
        env["DISPLAY"] = self.VIRTUAL_DISPLAY
        return env
    
    # ==================== STARTUP ====================
    
    def start(self) -> str:
        """Virtual workspace'i başlat (Xvfb + Remmina)."""
        if self._is_running:
            return "Virtual workspace zaten çalışıyor."
        
        # Önce eski süreçleri temizle
        self.stop()
        
        script_path = os.path.join(
            os.path.dirname(__file__), 
            "..", "..", "scripts", "start_workspace.sh"
        )
        
        # Script'i absolute path ile çalıştır
        script_path = os.path.abspath(script_path)
        
        if not os.path.exists(script_path):
            return f"❌ Script bulunamadı: {script_path}"
        
        # Script'i foreground'da çalıştır (kendi içinde arka plan süreçleri başlatır)
        try:
            result = subprocess.run(
                ["bash", script_path],
                capture_output=True,
                text=True,
                timeout=15  # 15 saniye timeout
            )
            
            if result.returncode == 0:
                self._is_running = True
                return "✅ Virtual workspace başlatıldı. Remmina 2. masaüstünde."
            else:
                return f"❌ Başlatma hatası: {result.stderr or result.stdout}"
        except subprocess.TimeoutExpired:
            # Timeout normal olabilir, süreçler arka planda çalışıyordur
            self._is_running = True
            return "✅ Virtual workspace başlatıldı (arka planda)."
        except Exception as e:
            return f"❌ Başlatma hatası: {str(e)}"
    
    def stop(self) -> str:
        """Virtual workspace'i durdur."""
        self._run_cmd(["pkill", "remmina"], capture=False)
        self._run_cmd(["pkill", "x11vnc"], capture=False)
        self._run_cmd(["pkill", "openbox"], capture=False)
        self._run_cmd(["pkill", "-f", f"Xvfb {self.VIRTUAL_DISPLAY}"], capture=False)
        
        self._is_running = False
        self._captured_window_id = None
        return "✅ Virtual workspace kapatıldı."
    
    # ==================== WINDOW CAPTURE ====================
    
    def capture_active_window(self) -> str:
        """
        Kullanıcının aktif penceresini yakala ve 2. masaüstüne taşı.
        Pencere artık Window ID ile kontrol edilecek.
        """
        # Aktif pencere ID'sini al
        code, window_id = self._run_cmd(["xdotool", "getactivewindow"])
        if code != 0 or not window_id:
            return "❌ Aktif pencere bulunamadı."
        
        self._captured_window_id = window_id
        
        # Pencere adını al (bilgi için)
        _, window_name = self._run_cmd(["xdotool", "getwindowname", window_id])
        
        # Pencereyi 2. masaüstüne taşı
        self._run_cmd(["wmctrl", "-i", "-r", window_id, "-t", str(self.TARGET_WORKSPACE)])
        
        # Kullanıcıyı 1. masaüstüne geri getir
        time.sleep(0.3)
        self._run_cmd(["wmctrl", "-s", "0"])
        
        return f"✅ '{window_name}' penceresi yakalandı ve 2. masaüstüne taşındı. Artık kontrol edebilirsin."
    
    def release_window(self) -> str:
        """Yakalanan pencereyi serbest bırak ve 1. masaüstüne geri getir."""
        if not self._captured_window_id:
            return "❌ Yakalanmış pencere yok."
        
        # Pencereyi 1. masaüstüne geri taşı
        self._run_cmd(["wmctrl", "-i", "-r", self._captured_window_id, "-t", "0"])
        
        # Pencereyi aktif et
        self._run_cmd(["wmctrl", "-i", "-a", self._captured_window_id])
        
        window_id = self._captured_window_id
        self._captured_window_id = None
        
        return f"✅ Pencere (ID: {window_id}) serbest bırakıldı ve önüne getirildi."

    def view_captured_window(self) -> str:
        """Yakalanan pencerenin görüntüsünü al (Screenshot)."""
        if not self._captured_window_id:
            return "❌ Yakalanmış pencere yok."
        
        # Screenshot için geçici dosya
        screenshot_path = os.path.join(os.getcwd(), "atom_workspace", "captured_window.png")
        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
        
        # xwd ile pencereyi yakala (background workspace'te olsa bile çalışabilir)
        # Not: Compositor yoksa black screen gelebilir.
        # Alternatif: import -window ID (ImageMagick)
        
        # Önce import dene (Daha temiz)
        code, _ = self._run_cmd(["import", "-window", self._captured_window_id, screenshot_path])
        
        if code != 0:
            # Import yoksa veya hata verdiyse xwd dene
            xwd_path = screenshot_path + ".xwd"
            c1, _ = self._run_cmd(["xwd", "-id", self._captured_window_id, "-out", xwd_path])
            c2, _ = self._run_cmd(["convert", xwd_path, screenshot_path])
            if c1 != 0 or c2 != 0:
                return "❌ Pencere görüntüsü alınamadı (xwd/import hatası)."
                
        return f"✅ Pencere görüntüsü alındı: {screenshot_path}\n(Görmek için 'view_file' kullanamazsın, bu bir görsel. Ama ben hafızama aldım varsay.)"

    
    # ==================== APP CONTROL ====================
    
    # Sanal ekran için ayrı Firefox profili kullanıyoruz
    # Bu sayede kullanıcının tarayıcısıyla çakışma olmaz
    WORKSPACE_BROWSER = "firefox -P atomik_workspace --no-remote --remote-debugging-port=9222"
    
    # Uygulama eşleştirme haritası
    APP_MAP = {
        # Native Apps
        "firefox": "firefox -P atomik_workspace --no-remote --remote-debugging-port=9222",
        "browser": "firefox -P atomik_workspace --no-remote --remote-debugging-port=9222",
        "tarayıcı": "firefox -P atomik_workspace --no-remote --remote-debugging-port=9222",
        "terminal": "gnome-terminal",
        "files": "nautilus",
        "code": "code",
        "gedit": "gedit",
        "libreoffice": "libreoffice",
        "onlyoffice": "flatpak run org.onlyoffice.desktopeditors",
        "gimp": "gimp",
        
        # Web Apps - Firefox ile ayrı profil (kullanıcının browserına karışmaz)
        "youtube": "firefox -P atomik_workspace --no-remote --remote-debugging-port=9222 https://www.youtube.com",
        "spotify": "firefox -P atomik_workspace --no-remote --remote-debugging-port=9222 https://open.spotify.com",
        "gmail": "firefox -P atomik_workspace --no-remote --remote-debugging-port=9222 https://mail.google.com",
        "whatsapp": "firefox -P atomik_workspace --no-remote --remote-debugging-port=9222 https://web.whatsapp.com",
        "chatgpt": "firefox -P atomik_workspace --no-remote --remote-debugging-port=9222 https://chatgpt.com",
        "github": "firefox -P atomik_workspace --no-remote --remote-debugging-port=9222 https://github.com",
        "google": "firefox -P atomik_workspace --no-remote --remote-debugging-port=9222 https://www.google.com",
    }
    
    def open_app(self, app_command: str, maximize: bool = True) -> str:
        """Sanal ekranda uygulama aç."""
        if not self._is_running:
            start_result = self.start()
            if "❌" in start_result:
                return start_result
        
        env = self._get_virtual_env()
        
        # Uygulama adını çözümle
        lower_app = app_command.lower().strip()
        
        # 1. APP_MAP kontrolü
        if lower_app in self.APP_MAP:
            cmd = self.APP_MAP[lower_app]
        # 2. URL kontrolü (Firefox atomik_workspace profili ile aç)
        elif lower_app.startswith(("http://", "https://", "www.")):
            cmd = f"firefox -P atomik_workspace --no-remote --remote-debugging-port=9222 {app_command}"
        elif "." in lower_app and " " not in lower_app:
            cmd = f"firefox -P atomik_workspace --no-remote --remote-debugging-port=9222 https://{app_command}"
        # 3. Direkt komut
        else:
            cmd = app_command
        
        # Uygulamayı başlat
        try:
            subprocess.Popen(
                cmd.split(),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            return f"❌ Uygulama başlatılamadı: {str(e)}"
        
        time.sleep(3)  # Uygulama başlaması için biraz daha bekle
        
        # Pencere adından ilk kelimeyi al
        window_hint = cmd.split()[0]
        
        # Pencereyi aktif et (fokus ver)
        self._run_cmd(
            ["wmctrl", "-a", window_hint],
            env=env
        )
        
        if maximize:
            self._run_cmd(
                ["wmctrl", "-r", window_hint, "-b", "add,maximized_vert,maximized_horz"],
                env=env
            )
        
        time.sleep(0.5)  # Fokus için bekle
        
        return f"✅ {app_command} sanal ekranda açıldı ve fokuslandı. (Komut: {cmd})"
    
    def type_text(self, text: str) -> str:
        """Aktif veya yakalanan pencereye metin yaz."""
        if self._captured_window_id:
            # Yakalanan pencereye yaz (Window ID ile)
            self._run_cmd([
                "xdotool", "type", "--window", self._captured_window_id,
                "--delay", "20", text
            ])
            return f"✅ Yakalanan pencereye yazıldı: {text[:50]}..."
        else:
            # Sanal ekrandaki aktif pencereye yaz
            env = self._get_virtual_env()
            self._run_cmd(["xdotool", "type", "--delay", "20", text], env=env)
            return f"✅ Sanal ekrana yazıldı: {text[:50]}..."
    
    def send_key(self, key: str) -> str:
        """Klavye tuşu gönder."""
        if self._captured_window_id:
            self._run_cmd([
                "xdotool", "key", "--window", self._captured_window_id, key
            ])
            return f"✅ Yakalanan pencereye tuş gönderildi: {key}"
        else:
            env = self._get_virtual_env()
            self._run_cmd(["xdotool", "key", key], env=env)
            return f"✅ Sanal ekrana tuş gönderildi: {key}"
    
    def click(self, x: int, y: int) -> str:
        """Belirtilen koordinata tıkla."""
        if self._captured_window_id:
            # Yakalanan pencerede tıkla (pencere-relative koordinat)
            self._run_cmd([
                "xdotool", "mousemove", "--window", self._captured_window_id,
                str(x), str(y)
            ])
            self._run_cmd(["xdotool", "click", "--window", self._captured_window_id, "1"])
            return f"✅ Yakalanan pencerede tıklandı: ({x}, {y})"
        else:
            env = self._get_virtual_env()
            self._run_cmd(["xdotool", "mousemove", str(x), str(y)], env=env)
            self._run_cmd(["xdotool", "click", "1"], env=env)
            return f"✅ Sanal ekranda tıklandı: ({x}, {y})"


# Singleton instance
workspace = VirtualWorkspace.get_instance()


# ==================== TOOL FUNCTIONS ====================

def start_virtual_workspace() -> str:
    """Virtual workspace'i başlat."""
    return workspace.start()

def stop_virtual_workspace() -> str:
    """Virtual workspace'i kapat."""
    return workspace.stop()

def capture_active_window() -> str:
    """Kullanıcının aktif penceresini yakala ve 2. masaüstüne taşı."""
    return workspace.capture_active_window()

def release_captured_window() -> str:
    """Yakalanan pencereyi serbest bırak ve kullanıcıya geri ver."""
    return workspace.release_window()

def open_app_in_workspace(app: str, maximize: bool = True) -> str:
    """Sanal ekranda uygulama aç."""
    return workspace.open_app(app, maximize)

def type_in_workspace(text: str) -> str:
    """Aktif/yakalanan pencereye metin yaz."""
    return workspace.type_text(text)

def send_key_in_workspace(key: str) -> str:
    """Aktif/yakalanan pencereye klavye tuşu gönder."""
    return workspace.send_key(key)

def click_in_workspace(x: int, y: int) -> str:
    """Aktif/yakalanan pencerede tıkla."""
    return workspace.click(x, y)

def focus_window_in_workspace(window_name: str) -> str:
    """Sanal ekrandaki belirli bir pencereye fokus ver."""
    env = workspace._get_virtual_env()
    code, _ = workspace._run_cmd(["wmctrl", "-a", window_name], env=env)
    if code == 0:
        return f"✅ '{window_name}' penceresine fokus verildi."
    else:
        return f"❌ '{window_name}' penceresi bulunamadı."

def view_captured_window() -> str:
    """Yakalanan pencerenin görüntüsünü al."""
    return workspace.view_captured_window()

