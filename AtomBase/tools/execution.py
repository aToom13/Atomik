"""
Terminal Command Execution with Permission System
"""
from langchain_core.tools import tool
import subprocess
import shlex
import os
import json
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
try:
    from config import config
except ImportError:
    try:
        from AtomBase.config import config
    except ImportError:
        # Fallback for when running directly
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from AtomBase.config import config
try:
    from utils.logger import get_logger
except ImportError:
    from AtomBase.utils.logger import get_logger

WORKSPACE_DIR = config.workspace.base_dir
logger = get_logger()

# Runtime'da eklenen izinli komutlar
_runtime_allowed_commands = set()

# Bekleyen komut onayları (UI tarafından kontrol edilir)
_pending_command = None
_command_callback = None


class CommandPermissionRequired(Exception):
    """Komut için izin gerektiğinde fırlatılır"""
    def __init__(self, command: str, base_cmd: str):
        self.command = command
        self.base_cmd = base_cmd
        super().__init__(f"Permission required for: {base_cmd}")


def add_allowed_command(cmd: str):
    """Runtime'da izinli komut ekler"""
    _runtime_allowed_commands.add(cmd)
    logger.info(f"Command added to allowed list: {cmd}")


def get_all_allowed_commands() -> list:
    """Tüm izinli komutları döndürür"""
    return list(config.execution.allowed_commands) + list(_runtime_allowed_commands)


def set_command_callback(callback):
    """UI'dan komut onay callback'i ayarlar"""
    global _command_callback
    _command_callback = callback


def execute_command_direct(command: str) -> str:
    """Actually execute the command and return output"""
    
    # Detect GUI/interactive commands that should run in background
    gui_indicators = ['pygame', 'tkinter', 'gtk', 'qt', 'kivy', 'flappy', 'game', 
                      'display', 'window', 'gui', 'firefox', 'chrome', 'code', 'gedit']
    
    is_gui_command = any(indicator in command.lower() for indicator in gui_indicators)
    
    # Also check for .py files that might be GUI apps
    if '.py' in command and not any(x in command for x in ['--help', '-h', '--version']):
        # Assume Python scripts might be GUI, run with short timeout first
        is_gui_command = True
    
    try:
        if is_gui_command:
            # Log stderr to file so errors can be tracked
            log_dir = os.path.join(WORKSPACE_DIR, ".logs")
            os.makedirs(log_dir, exist_ok=True)
            
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            log_file = os.path.join(log_dir, f"app_{timestamp}.log")
            
            # Open log file for stderr
            stderr_log = open(log_file, 'w')
            
            # Use user's default display (NOT virtual display :99)
            # Virtual display is only used via open_app_in_workspace explicitly
            
            # Run GUI apps in background (non-blocking) with stderr logging
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=WORKSPACE_DIR,
                stdout=subprocess.DEVNULL,
                stderr=stderr_log,
                start_new_session=True  # Detach from parent
            )
            
            # Wait briefly to detect immediate crashes
            time.sleep(1.0)
            
            # Check if process crashed immediately
            poll_result = process.poll()
            if poll_result is not None:
                # Process ended - likely crashed
                stderr_log.close()
                
                # Read error log
                with open(log_file, 'r') as f:
                    error_content = f.read().strip()
                
                if error_content:
                    # Truncate if too long
                    if len(error_content) > 500:
                        error_content = error_content[:500] + "..."
                    return f"❌ Uygulama çöktü (kod: {poll_result}):\n{error_content}"
                else:
                    return f"❌ Uygulama hemen kapandı (kod: {poll_result}). Log boş."
            
            # Process is still running
            return f"✓ Uygulama başladı (PID: {process.pid}). Konuşmaya devam edebilirsin!"
        else:
            # Regular commands - run synchronously with timeout
            result = subprocess.run(
                command,
                shell=True,
                cwd=WORKSPACE_DIR,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]: {result.stderr}"
            
            if not output.strip():
                output = "✓ Komut başarıyla çalıştı (çıktı yok)"
            
            # Truncate if too long
            if len(output) > 2000:
                output = output[:2000] + "\n... (kırpıldı)"
            
            return output
        
    except subprocess.TimeoutExpired:
        return "❌ Komut zaman aşımına uğradı (30 saniye)"
    except Exception as e:
        return f"❌ Komut hatası: {str(e)}"


def _is_command_safe(command: str) -> tuple[bool, str, str]:
    """
    Komutu güvenlik açısından kontrol eder.
    Returns: (is_safe, reason, base_cmd)
    """
    # Blocked patterns kontrolü
    for pattern in config.execution.blocked_patterns:
        if pattern.lower() in command.lower():
            return False, f"Blocked: {pattern}", ""
    
    # Tehlikeli karakterler
    dangerous_chars = [';', '&&', '||', '`', '$(']
    for char in dangerous_chars:
        if char in command:
            return False, f"Dangerous: {char}", ""
    
    # İlk komutun allowed listesinde olup olmadığını kontrol et
    try:
        parts = shlex.split(command)
        if parts:
            base_cmd = os.path.basename(parts[0])
            all_allowed = get_all_allowed_commands()
            
            if base_cmd not in all_allowed:
                return False, f"Not allowed: {base_cmd}", base_cmd
    except ValueError:
        return False, "Invalid syntax", ""
    
    return True, "OK", ""


@tool
def run_terminal_command(command: str) -> str:
    """
    Executes a terminal command in the workspace.
    
    Args:
        command: Command to execute (e.g., 'python script.py')
        
    Returns:
        Command output or error message
    """
    logger.info(f"Command: {command}")
    
    # Güvenlik kontrolü
    is_safe, reason, base_cmd = _is_command_safe(command)
    
    if not is_safe:
        if base_cmd:
            # İzin gerekiyor - özel mesaj döndür
            logger.warning(f"Permission needed: {base_cmd}")
            return f"⚠️ PERMISSION_REQUIRED:{base_cmd}:{command}"
        else:
            # Tamamen engellendi
            logger.warning(f"Blocked: {command}")
            return f"❌ {reason}"
    
    # Güvenli, çalıştır
    return execute_command_direct(command)

@tool
def open_application(app_name: str) -> str:
    """
    Doğrudan uygulama başlatır (Mappings + URL + Fallback)
    """
    # 1. MAPPINGS
    APP_MAP = {
        # Native Apps
        "zen": "flatpak run app.zen_browser.zen --remote-debugging-port=9222", # Debug port ile başlat
        "browser": "flatpak run app.zen_browser.zen --remote-debugging-port=9222",
        "tarayıcı": "flatpak run app.zen_browser.zen --remote-debugging-port=9222",
        "firefox": "firefox",
        "terminal": "gnome-terminal",
        "files": "nautilus",
        "code": "code", # Fallback
        
        # Web Apps (Always open in Zen with Debug Port)
        "youtube": "flatpak run app.zen_browser.zen --remote-debugging-port=9222 --new-tab https://www.youtube.com",
        "spotify": "flatpak run app.zen_browser.zen --remote-debugging-port=9222 --new-tab https://open.spotify.com",
        "gmail": "flatpak run app.zen_browser.zen --remote-debugging-port=9222 --new-tab https://mail.google.com",
        "whatsapp": "flatpak run app.zen_browser.zen --remote-debugging-port=9222 --new-tab https://web.whatsapp.com",
        "chatgpt": "flatpak run app.zen_browser.zen --remote-debugging-port=9222 --new-tab https://chatgpt.com",
        "github": "flatpak run app.zen_browser.zen --remote-debugging-port=9222 --new-tab https://github.com",
    }
    
    cmd = ""
    lower_app = app_name.lower().strip()
    
    # 1. Mapping kontrolü
    if lower_app in APP_MAP:
        cmd = APP_MAP[lower_app]
    
    # 2. URL kontrolü (http/https veya .com/.org vb.)
    elif lower_app.startswith(("http://", "https://", "www.")):
        cmd = f"flatpak run app.zen_browser.zen --remote-debugging-port=9222 --new-tab {app_name}"
    elif "." in lower_app and " " not in lower_app: # Örn: google.com, atomik.app
        cmd = f"flatpak run app.zen_browser.zen --remote-debugging-port=9222 --new-tab https://{app_name}"
    
    # 3. Fallback (Direkt komut olarak)
    else:
        # Basit güvenlik kontrolü (sadece alfanümerik ve tire)
        import re
        if re.match(r"^[a-zA-Z0-9_-]+$", lower_app):
            cmd = lower_app
        else:
            return f"❌ Geçersiz uygulama adı: {app_name} (Güvenlik nedeniyle çalıştırılmadı)"

    logger.info(f"Open Application: {app_name} -> {cmd}")
    
    # Arka planda çalıştır (Asenkron) - Timeout sorununu önlemek için
    try:
        import subprocess
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        return f"✅ Uygulama başlatıldı: {app_name} ({cmd})"
    except Exception as e:
        return f"❌ Başlatma hatası: {str(e)}"
