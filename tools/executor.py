"""
Tool Executor - Execute AtomBase tools
"""
import os
import sys

# Ensure project root is in path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core import state
from core.colors import Colors

# ===== NEW: Unified Memory & Error Handler =====
try:
    from tools.memory.unified_memory import get_memory_system
    UNIFIED_MEMORY_AVAILABLE = True
except ImportError:
    get_memory_system = None
    UNIFIED_MEMORY_AVAILABLE = False

try:
    from core.error_handler import get_error_handler, get_atomik_logger
    ERROR_HANDLER_AVAILABLE = True
except ImportError:
    get_error_handler = None
    get_atomik_logger = None
    ERROR_HANDLER_AVAILABLE = False
# ===============================================

# AtomBase tool imports
ATOMBASE_AVAILABLE = False
CODING_AVAILABLE = False
MEMORY_AVAILABLE = False
WEATHER_AVAILABLE = False
CAMERA_AVAILABLE = False
VISUAL_MEMORY_AVAILABLE = False
CAMERA_ENABLED = False

# Add AtomBase to path for its internal imports
_atombase_path = os.path.join(_project_root, "AtomBase")
if _atombase_path not in sys.path:
    sys.path.insert(0, _atombase_path)

try:
    from AtomBase.tools.basic import get_current_time, run_neofetch
    from tools.system.location import get_current_location
    from AtomBase.tools.files import list_files, read_file, write_file, scan_workspace
    from AtomBase.tools.execution import run_terminal_command
    from tools.dev.coding import delegate_coding, save_generated_code
    from AtomBase.tools.memory import (
        save_context, get_context_info, get_memory_stats, clear_memory,
        add_to_history, get_all_context, get_user_name
    )
    from tools.system.weather import get_weather
    from tools.system.camera import capture_frame, get_camera_payload
    from tools.memory.visual_memory import (
        save_visual_observation, get_visual_history, 
        compare_with_last, get_visual_context_for_prompt
    )
    ATOMBASE_AVAILABLE = True
    CODING_AVAILABLE = True
    MEMORY_AVAILABLE = True
    WEATHER_AVAILABLE = True
    CAMERA_AVAILABLE = True
    VISUAL_MEMORY_AVAILABLE = True
    CAMERA_ENABLED = CAMERA_AVAILABLE
except ImportError as e:
    print(f"{Colors.YELLOW}AtomBase araçları yüklenemedi: {e}{Colors.RESET}")


def execute_tool(name: str, args: dict) -> str:
    """Execute an AtomBase tool and return the result."""
    try:
        if name == "get_current_time":
            return get_current_time.invoke({})
        elif name == "get_current_location":
            import json
            # Use cached location if available (fetched at startup)
            if state.cached_location:
                return json.dumps(state.cached_location, ensure_ascii=False)
            result = get_current_location.invoke({})
            return json.dumps(result, ensure_ascii=False)
        elif name == "list_files":
            return list_files.invoke({"directory": args.get("directory", ".")})
        elif name == "read_file":
            return read_file.invoke({"filename": args["filename"]})
        elif name == "write_file":
            return write_file.invoke({"filename": args["filename"], "content": args["content"]})
        elif name == "scan_workspace":
            return scan_workspace.invoke({"max_depth": args.get("max_depth", 2)})
        elif name == "run_terminal_command":
            return run_terminal_command.invoke({"command": args["command"]})
        elif name == "run_neofetch":
            return run_neofetch.invoke({})
        elif name == "delegate_coding":
            if CODING_AVAILABLE:
                result = delegate_coding(args["prompt"], args.get("context", ""))
                if result["success"]:
                    import os as os_module  # Avoid shadowing from nested imports
                    workspace = os_module.path.join(os_module.path.dirname(os_module.path.dirname(__file__)), "atom_workspace")
                    os_module.makedirs(workspace, exist_ok=True)
                    filepath = save_generated_code(result["filename"], result["code"], workspace)
                    return f"✅ Kod oluşturuldu: {result['filename']}\n\n{result['explanation']}\n\nDosya: {filepath}"
                else:
                    return f"❌ Kod oluşturulamadı: {result.get('error', 'Bilinmeyen hata')}"
            return "Coding module not available"
        # Memory tools
        elif name == "save_context":
            if MEMORY_AVAILABLE:
                return save_context(args["key"], args["value"])
            return "Memory module not available"
        elif name == "get_context_info":
            if MEMORY_AVAILABLE:
                return get_context_info(args["key"])
            return "Memory module not available"
        elif name == "get_memory_stats":
            if MEMORY_AVAILABLE:
                return get_memory_stats()
            return "Memory module not available"
        elif name == "clear_memory":
            if MEMORY_AVAILABLE:
                return clear_memory()
            return "Memory module not available"
        # Weather tool
        elif name == "get_weather":
            if WEATHER_AVAILABLE:
                return get_weather(args["city"])
            return "Weather module not available"
        # Camera tool removed - frames are sent automatically via VAD in audio/video.py
        # Exit tool
        elif name == "exit_app":
            state.exit_requested = True
            return "Güle güle! Seninle sohbet etmek güzeldi. Tekrar görüşmek üzere!"
        # Visual Memory Tools
        elif name == "save_visual_observation":
            if VISUAL_MEMORY_AVAILABLE:
                return save_visual_observation(args["notes"])
            return "Görsel hafıza kullanılamıyor"
        elif name == "get_visual_history":
            if VISUAL_MEMORY_AVAILABLE:
                return get_visual_history()
            return "Görsel hafıza kullanılamıyor"
        # Screen Sharing Tools
        elif name == "share_screen":
            state.video_mode = "screen"
            return "🖥️ Tamam! Kamerayı kapatıp ekranını izlemeye başlıyorum. 'Ekranı bırakabilirsin' dediğinde geri kameraya döneceğim."
        elif name == "stop_screen_share":
            state.video_mode = "camera"
            return "📷 Ekran paylaşımı durduruldu. Kameraya geri dönüyorum!"
        elif name == "share_workspace_screen":
            state.video_mode = "workspace"
            return "🖥️ Sanal ekranı (Virtual Workspace) izlemeye başlıyorum. Artık 2. masaüstündeki uygulamaları görebiliyorum!"
        # Proactive Tools
        elif name == "set_reminder":
            from core.proactive import set_reminder as _set_reminder
            return _set_reminder(args["duration_seconds"], args["message"])
        elif name == "set_watcher":
            from core.proactive import set_watcher as _set_watcher
            return _set_watcher(args["condition"], args["message"])
            
        elif name == "learn_proactive_rule":
            from core.learning import add_vision_rule
            return add_vision_rule(args.get("rule"))
            
        elif name == "computer_control":
            from core.computer import mouse_move, mouse_click, keyboard_type, keyboard_key
            action = args.get("action")
            if action == "move":
                return mouse_move(args.get("x"), args.get("y"))
            elif action == "click":
                return mouse_click(x=args.get("x"), y=args.get("y"))
            elif action == "type":
                return keyboard_type(args.get("text"))
            elif action == "key":
                return keyboard_key(args.get("text"))
            return "Unknown action"
            
        elif name == "find_ui_element":
            from core.vision_analyzer import find_element_on_screen
            from core.state import latest_image_payload
            from core.computer import get_screen_size
            import asyncio
            import threading
            
            # Use active state to get image
            if not latest_image_payload:
                return "Error: No screen image available."
            
            # Run async function in a new loop in a new thread to be safe
            result_container = {}
            
            def run_in_thread(element, image, container):
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    res = new_loop.run_until_complete(find_element_on_screen(element, image))
                    container['result'] = res
                    new_loop.close()
                except Exception as e:
                    container['error'] = str(e)

            # Start thread and join (blocking this tool execution, but that's what we want for sync return)
            t = threading.Thread(target=run_in_thread, args=(args.get("element_name"), latest_image_payload, result_container))
            t.start()
            t.join(timeout=10) # 10s timeout
            
            if t.is_alive():
                 return "Error: Timeout looking for element."
                 
            result = result_container.get("result", {})
            error = result_container.get("error")
            
            if error:
                return f"Error finding element: {error}"
            
            if result.get("found"):
                # Convert 0-1000 to pixels
                # Assume 1920x1080 for now if get_screen_size fails
                WIDTH, HEIGHT = 1920, 1080
                try:
                    # Parse "1920x1080" from get_screen_size
                    dims = get_screen_size().strip().split("x")
                    if len(dims) == 2:
                        WIDTH, HEIGHT = int(dims[0]), int(dims[1])
                except:
                    pass
                    
                # Gemini returns [ymin, xmin, ymax, xmax] 0-1000
                coords = result.get("coordinates") #[ymin, xmin, ymax, xmax]
                if coords:
                    ymin, xmin, ymax, xmax = coords
                    center_x_norm = (xmin + xmax) / 2
                    center_y_norm = (ymin + ymax) / 2
                else:
                    center_x_norm = result.get("center_x", 500)
                    center_y_norm = result.get("center_y", 500)
                
                pixel_x = int((center_x_norm / 1000) * WIDTH)
                pixel_y = int((center_y_norm / 1000) * HEIGHT)
                
                return f"Found '{args.get('element_name')}' at [{pixel_x}, {pixel_y}]. Use computer_control(action='click', x={pixel_x}, y={pixel_y}) to click."
            else:
                return f"Could not find '{args.get('element_name')}' on screen."
        
        # Clipboard Tools
        elif name == "clipboard_read":
            import pyperclip
            try:
                text = pyperclip.paste()
                if text:
                    return f"📋 Panodaki metin: {text[:500]}{'...' if len(text) > 500 else ''}"
                else:
                    return "📋 Pano boş."
            except Exception as e:
                return f"Pano okunamadı: {str(e)}"
        
        elif name == "clipboard_write":
            import pyperclip
            text = args.get("text", "")
            try:
                pyperclip.copy(text)
                return f"✅ Metin panoya kopyalandı ({len(text)} karakter)"
            except Exception as e:
                return f"Panoya yazılamadı: {str(e)}"
        
        # Web Search Tool
        elif name == "web_search":
            import requests
            from bs4 import BeautifulSoup
            import urllib.parse
            import os
            
            query = args.get("query", "")
            num_results = args.get("num_results", 5)
            results = []
            
            # ===== Method 1: Tavily API with Key Rotation =====
            tavily_keys_str = os.environ.get("TAVILY_API_KEYS", "")
            if tavily_keys_str:
                tavily_keys = [k.strip() for k in tavily_keys_str.split(",") if k.strip()]
                
                for key_idx, api_key in enumerate(tavily_keys):
                    try:
                        from tavily import TavilyClient
                        client = TavilyClient(api_key=api_key)
                        
                        response = client.search(query, max_results=num_results, search_depth="basic")
                        
                        if response and response.get("results"):
                            for i, r in enumerate(response["results"][:num_results]):
                                title = r.get("title", "")
                                url = r.get("url", "")
                                snippet = r.get("content", "")[:100] + "..." if r.get("content") else ""
                                results.append(f"{i+1}. {title}\n   {url}\n   {snippet}")
                            break  # Success, exit key loop
                            
                    except Exception as e:
                        error_str = str(e).lower()
                        if "rate limit" in error_str or "429" in error_str or "quota" in error_str:
                            continue  # Try next key
                        else:
                            break  # Other error, try fallback methods
            
            # Helper to clean DuckDuckGo redirect URLs
            def clean_ddg_url(url):
                if 'duckduckgo.com/l/?uddg=' in url or 'uddg=' in url:
                    try:
                        # Extract actual URL from uddg parameter
                        if 'uddg=' in url:
                            actual = url.split('uddg=')[1].split('&')[0]
                            return urllib.parse.unquote(actual)
                    except:
                        pass
                return url
            
            # ===== Method 2: DuckDuckGo API fallback =====
            if not results:
                try:
                    from duckduckgo_search import DDGS
                    with DDGS() as ddgs:
                        # Use Turkish region for better results
                        for i, r in enumerate(ddgs.text(query, region='tr-tr', max_results=num_results)):
                            clean_href = clean_ddg_url(r['href'])
                            results.append(f"{i+1}. {r['title']}\n   {clean_href}")
                except Exception:
                    pass
            
            # ===== Method 3: DuckDuckGo HTML fallback =====
            if not results:
                try:
                    encoded_query = urllib.parse.quote_plus(query)
                    url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
                    response = requests.get(url, headers=headers, timeout=10)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    for result in soup.find_all('div', class_='result')[:num_results]:
                        title_elem = result.find('a', class_='result__a')
                        if title_elem:
                            title = title_elem.get_text()
                            href = clean_ddg_url(title_elem.get('href', ''))
                            if title and href:
                                results.append(f"{len(results)+1}. {title}\n   {href}")
                except Exception:
                    pass
            
            if results:
                return f"🔍 '{query}' için sonuçlar:\n" + "\n".join(results)
            else:
                return f"'{query}' için sonuç bulunamadı. İnternet bağlantısını kontrol et."
        
        # Notification Tool
        elif name == "show_notification":
            try:
                from plyer import notification
                title = args.get("title", "Atomik")
                message = args.get("message", "")
                
                notification.notify(
                    title=title,
                    message=message,
                    app_name="Atomik",
                    timeout=10
                )
                return f"🔔 Bildirim gösterildi: {title}"
            except Exception as e:
                return f"Bildirim gösterilemedi: {str(e)}"
        
        # ===== RAG MEMORY TOOLS =====
        elif name == "remember_this":
            try:
                from tools.memory.rag_memory import remember_conversation
                summary = args.get("summary", "")
                topic = args.get("topic", "")
                
                metadata = {"topic": topic} if topic else None
                return remember_conversation(summary, metadata)
            except Exception as e:
                return f"Hafıza hatası: {str(e)}"
        
        elif name == "recall_memory":
            try:
                from tools.memory.rag_memory import recall_memory
                query = args.get("query", "")
                return recall_memory(query)
            except Exception as e:
                return f"Hatırlama hatası: {str(e)}"
        
        elif name == "get_recent_memories":
            try:
                from tools.memory.rag_memory import get_recent_memories
                days = args.get("days", 7)
                return get_recent_memories(days)
            except Exception as e:
                return f"Anı getirme hatası: {str(e)}"
        
        # ===== WEB SCRAPER TOOL =====
        elif name == "visit_webpage":
            try:
                import requests
                from bs4 import BeautifulSoup
                
                url = args.get("url", "")
                if not url:
                    return "URL belirtilmedi."
                
                # Add protocol if missing
                if not url.startswith("http"):
                    url = "https://" + url
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
                }
                
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove scripts, styles, nav, footer
                for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form']):
                    tag.decompose()
                
                # Get title
                title = soup.title.string if soup.title else "Başlık yok"
                
                # Get main content
                main = soup.find('main') or soup.find('article') or soup.find('body')
                if main:
                    text = main.get_text(separator='\n', strip=True)
                else:
                    text = soup.get_text(separator='\n', strip=True)
                
                # Clean up whitespace
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                text = '\n'.join(lines)
                
                # Truncate for token efficiency
                max_chars = 3000
                if len(text) > max_chars:
                    text = text[:max_chars] + "...\n[İçerik kısaltıldı]"
                
                return f"📄 {title}\n\n{text}"
                
            except requests.exceptions.Timeout:
                return "❌ Sayfa yüklenemedi: Zaman aşımı"
            except requests.exceptions.RequestException as e:
                return f"❌ Sayfa yüklenemedi: {str(e)}"
            except Exception as e:
                return f"❌ Sayfa okuma hatası: {str(e)}"
        
        # ===== SESSION HISTORY TOOLS =====
        elif name == "search_chat_history":
            try:
                from tools.memory.session_db import search_history
                query = args.get("query", "")
                return search_history(query)
            except Exception as e:
                return f"Geçmiş arama hatası: {str(e)}"
        
        elif name == "get_chat_stats":
            try:
                from tools.memory.session_db import get_stats
                return get_stats()
            except Exception as e:
                return f"İstatistik hatası: {str(e)}"
        
        # ===== CODE QUALITY TOOLS =====
        elif name == "run_linter":
            try:
                import subprocess
                file_path = args.get("file_path", "")
                
                if not file_path:
                    return "❌ Dosya yolu belirtilmedi."
                
                import os as os_module  # Avoid shadowing from nested imports
                if not os_module.path.exists(file_path):
                    return f"❌ Dosya bulunamadı: {file_path}"
                
                # Try flake8 first, then pylint
                try:
                    result = subprocess.run(
                        ["flake8", "--max-line-length=120", file_path],
                        capture_output=True, text=True, timeout=30
                    )
                    output = result.stdout + result.stderr
                except FileNotFoundError:
                    result = subprocess.run(
                        ["python3", "-m", "py_compile", file_path],
                        capture_output=True, text=True, timeout=30
                    )
                    output = result.stderr if result.returncode != 0 else "✅ Sözdizimi hatası yok."
                
                if not output.strip():
                    return f"✅ {os_module.path.basename(file_path)} - Lint hatası yok!"
                
                # Truncate if too long
                if len(output) > 1000:
                    output = output[:1000] + "\n...[kısaltıldı]"
                
                return f"🔍 Lint Sonuçları ({os_module.path.basename(file_path)}):\n{output}"
                
            except subprocess.TimeoutExpired:
                return "❌ Lint zaman aşımına uğradı."
            except Exception as e:
                return f"❌ Lint hatası: {str(e)}"
        
        elif name == "format_code":
            try:
                import subprocess
                file_path = args.get("file_path", "")
                
                if not file_path:
                    return "❌ Dosya yolu belirtilmedi."
                
                if not os.path.exists(file_path):
                    return f"❌ Dosya bulunamadı: {file_path}"
                
                # Use black for formatting
                try:
                    result = subprocess.run(
                        ["black", "--line-length=100", file_path],
                        capture_output=True, text=True, timeout=30
                    )
                    if result.returncode == 0:
                        return f"✅ {os.path.basename(file_path)} formatlandı!"
                    else:
                        return f"⚠️ Format uyarısı: {result.stderr[:500]}"
                except FileNotFoundError:
                    return "❌ 'black' yüklü değil. `pip install black` çalıştır."
                
            except subprocess.TimeoutExpired:
                return "❌ Format zaman aşımına uğradı."
            except Exception as e:
                return f"❌ Format hatası: {str(e)}"
        
        elif name == "run_tests":
            try:
                import subprocess
                path = args.get("path", "")
                
                cmd = ["pytest", "-v", "--tb=short"]
                if path:
                    cmd.append(path)
                
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=120,
                        cwd=os.getcwd()
                    )
                    output = result.stdout + result.stderr
                except FileNotFoundError:
                    return "❌ 'pytest' yüklü değil. `pip install pytest` çalıştır."
                
                # Truncate if too long
                if len(output) > 1500:
                    output = output[:1500] + "\n...[kısaltıldı]"
                
                if result.returncode == 0:
                    return f"✅ Testler başarılı!\n\n{output}"
                else:
                    return f"❌ Bazı testler başarısız:\n\n{output}"
                
            except subprocess.TimeoutExpired:
                return "❌ Testler zaman aşımına uğradı (2 dk)."
            except Exception as e:
                return f"❌ Test hatası: {str(e)}"
        
        # ===== LEARNING TOOLS =====
        elif name == "log_mood":
            try:
                from tools.memory.learning import log_mood
                mood = args.get("mood", "neutral")
                context = args.get("context", "")
                return log_mood(mood, context)
            except Exception as e:
                return f"❌ Mood kaydetme hatası: {str(e)}"
        
        elif name == "update_preference":
            try:
                from tools.memory.learning import update_preference
                key = args.get("key", "")
                value = args.get("value", "")
                if not key or not value:
                    return "❌ Anahtar ve değer gerekli."
                return update_preference(key, value)
            except Exception as e:
                return f"❌ Tercih kaydetme hatası: {str(e)}"
        
        elif name == "add_project":
            try:
                from tools.memory.learning import add_project
                name_val = args.get("name", "")
                status = args.get("status", "active")
                if not name_val:
                    return "❌ Proje adı gerekli."
                return add_project(name_val, status)
            except Exception as e:
                return f"❌ Proje kaydetme hatası: {str(e)}"
        
        elif name == "open_application":
            try:
                from AtomBase.tools.execution import open_application
                app_name_arg = args.get("app_name", "")
                if not app_name_arg:
                    return "❌ Uygulama adı gerekli."
                return open_application.invoke({"app_name": app_name_arg})
            except Exception as e:
                return f"❌ Uygulama açma hatası: {str(e)}"
        
        elif name == "inspect_web_page":
            try:
                from tools.web.web_inspector import inspect_web_page
                port = args.get("port", 9222)
                return inspect_web_page.invoke({"port": port})
            except Exception as e:
                return f"❌ DOM analiz hatası: {str(e)}"
        
        # ===== VIRTUAL WORKSPACE TOOLS =====
        elif name == "start_virtual_workspace":
            try:
                from tools.system.workspace import start_virtual_workspace
                return start_virtual_workspace()
            except Exception as e:
                return f"❌ Virtual workspace başlatma hatası: {str(e)}"
        
        elif name == "stop_virtual_workspace":
            try:
                from tools.system.workspace import stop_virtual_workspace
                return stop_virtual_workspace()
            except Exception as e:
                return f"❌ Virtual workspace durdurma hatası: {str(e)}"
        
        elif name == "capture_active_window":
            try:
                from tools.system.workspace import capture_active_window
                return capture_active_window()
            except Exception as e:
                return f"❌ Pencere yakalama hatası: {str(e)}"
        
        elif name == "release_captured_window":
            try:
                from tools.system.workspace import release_captured_window
                return release_captured_window()
            except Exception as e:
                return f"❌ Pencere serbest bırakma hatası: {str(e)}"
        
        elif name == "open_app_in_workspace":
            try:
                from tools.system.workspace import open_app_in_workspace
                app = args.get("app", "")
                maximize = args.get("maximize", True)
                if not app:
                    return "❌ Uygulama komutu gerekli."
                return open_app_in_workspace(app, maximize)
            except Exception as e:
                return f"❌ Uygulama açma hatası: {str(e)}"
        
        elif name == "type_in_workspace":
            try:
                from tools.system.workspace import type_in_workspace
                text = args.get("text", "")
                if not text:
                    return "❌ Metin gerekli."
                return type_in_workspace(text)
            except Exception as e:
                return f"❌ Yazma hatası: {str(e)}"
        
        elif name == "send_key_in_workspace":
            try:
                from tools.system.workspace import send_key_in_workspace
                key = args.get("key", "")
                if not key:
                    return "❌ Tuş gerekli."
                return send_key_in_workspace(key)
            except Exception as e:
                return f"❌ Tuş gönderme hatası: {str(e)}"
        
        elif name == "click_in_workspace":
            try:
                from tools.system.workspace import click_in_workspace
                x = args.get("x")
                y = args.get("y")
                if x is None or y is None:
                    return "❌ X ve Y koordinatları gerekli."
                return click_in_workspace(x, y)
            except Exception as e:
                return f"❌ Tıklama hatası: {str(e)}"
        
        elif name == "focus_window_in_workspace":
            try:
                from tools.system.workspace import focus_window_in_workspace
                window_name = args.get("window_name", "")
                if not window_name:
                    return "❌ Pencere adı gerekli."
                return focus_window_in_workspace(window_name)
            except Exception as e:
                return f"❌ Fokus hatası: {str(e)}"
        
        # ===== CALCODER PRO TOOLS =====
        elif name == "write_code_advanced":
            try:
                from tools.dev.calcoder_pro import write_code_advanced
                task = args.get("task", "")
                if not task:
                    return "❌ Görev (task) gerekli."
                complexity = args.get("complexity", "auto")
                context = args.get("context", None)
                result = write_code_advanced(task, complexity, context)
                
                status = result.get("status", "")
                if status in ["success", "fixed", "partial"]:
                    files = result.get("files") or {result.get("filename"): result.get("code")}
                    file_list = ", ".join(files.keys()) if files else "?"
                    message = result.get("message", "Kod oluşturuldu!")
                    filepath = result.get("filepath", "atom_workspace/")
                    
                    # Stats varsa ekle
                    stats = result.get("stats")
                    if stats:
                        message += f"\n📊 {stats.get('total_files', 0)} dosya, {stats.get('fixed_count', 0)} düzeltme"
                    
                    return f"✅ {message}\nDosyalar: {file_list}"
                else:
                    # Hata durumu - detaylı bilgi göster
                    error = result.get("error", "")
                    details = result.get("details", [])
                    message = result.get("message", "Kod oluşturulamadı")
                    
                    error_text = f"❌ {message}"
                    if error:
                        error_text += f"\nHata: {error}"
                    if details:
                        error_text += f"\nDetaylar: {'; '.join(details[:3])}"
                    
                    return error_text
            except Exception as e:
                import traceback
                logger.error(f"CalcoderPro exception: {traceback.format_exc()}")
                return f"❌ CalcoderPro hatası: {str(e)}"
        
        elif name == "fix_code_file":
            try:
                from tools.dev.calcoder_pro import fix_code_file
                filename = args.get("filename", "")
                error_message = args.get("error_message", "")
                if not filename or not error_message:
                    return "❌ Dosya adı ve hata mesajı gerekli."
                result = fix_code_file(filename, error_message)
                
                if result.get("status") == "fixed":
                    return f"✅ Kod düzeltildi ({result.get('attempts', 1)}. denemede)."
                else:
                    return f"❌ Düzeltilemedi: {result.get('error', 'Bilinmeyen hata')}"
            except Exception as e:
                return f"❌ Düzeltme hatası: {str(e)}"
        
        elif name == "run_code_tests":
            try:
                from tools.dev.calcoder_pro import run_code_tests
                # Accept both 'filename' and 'path' parameters
                filename = args.get("filename") or args.get("path", "")
                if not filename:
                    return "❌ Dosya adı gerekli."
                
                # If it's a full path, extract filename
                if "/" in filename:
                    filename = filename.split("/")[-1]
                
                result = run_code_tests(filename)
                
                if result.get("success"):
                    return f"✅ Test başarılı!\n{result.get('output', '')[:500]}"
                else:
                    return f"❌ Test başarısız: {result.get('error', '')[:500]}"
            except Exception as e:
                return f"❌ Test hatası: {str(e)}"
        
        # ===== UNIFIED VISION TOOL =====
        elif name == "see_screen":
            try:
                from core.unified_vision import see_screen as _see_screen
                task = args.get("task")  # "oku", "anla", None
                region = args.get("region")  # "alt", "üst-sağ", etc.
                find = args.get("find")  # element name to find
                
                result = _see_screen(task=task, region=region, find=find)
                
                if "error" in result:
                    return f"❌ Görme hatası: {result['error']}"
                
                # Format response based on task type
                if find:
                    # Element finding mode
                    if result.get("found"):
                        coords = result.get("coordinates", [])
                        cx = result.get("center_x", 500)
                        cy = result.get("center_y", 500)
                        
                        # Convert to pixels (assume 1920x1080)
                        from core.computer import get_screen_size
                        WIDTH, HEIGHT = 1920, 1080
                        try:
                            dims = get_screen_size().strip().split("x")
                            if len(dims) == 2:
                                WIDTH, HEIGHT = int(dims[0]), int(dims[1])
                        except:
                            pass
                        
                        pixel_x = int((cx / 1000) * WIDTH)
                        pixel_y = int((cy / 1000) * HEIGHT)
                        
                        return f"✅ '{find}' bulundu: [{pixel_x}, {pixel_y}]\n📍 {result.get('description', '')}"
                    else:
                        return f"❌ '{find}' bulunamadı. {result.get('description', '')}"
                
                elif task in ["oku", "read", "metin"]:
                    # Text reading mode
                    urls = result.get("urls", [])
                    all_text = result.get("all_text", "")
                    important = result.get("important_text", [])
                    
                    response = f"📖 Ekrandaki Metinler:\n{all_text[:1500]}"
                    if urls:
                        response += f"\n\n🔗 Bulunan URL'ler:\n" + "\n".join(f"  • {u}" for u in urls)
                    if important:
                        response += f"\n\n⭐ Önemli:\n" + "\n".join(f"  • {t}" for t in important[:5])
                    
                    return response
                
                else:
                    # General analysis mode
                    app = result.get("application", "Bilinmiyor")
                    activity = result.get("activity", "")
                    summary = result.get("content_summary", "")
                    items = result.get("important_items", [])
                    errors = result.get("errors_or_warnings", [])
                    
                    response = f"🖥️ {app}\n📝 {activity}\n📋 {summary}"
                    if items:
                        response += f"\n\n📌 Önemli:\n" + "\n".join(f"  • {i}" for i in items[:5])
                    if errors:
                        response += f"\n\n⚠️ Hatalar:\n" + "\n".join(f"  • {e}" for e in errors[:3])
                    
                    return response
                    
            except Exception as e:
                return f"❌ Görme hatası: {str(e)}"
        
        # Legacy vision tools (deprecated - redirect to see_screen)
        elif name in ["analyze_view", "identify_object", "read_my_emotion", 
                      "analyze_screen_content", "detect_gesture"]:
            return f"⚠️ '{name}' eskimiş araç. Bunun yerine 'see_screen' kullan."
        
        # ===== CONTEXTUAL LEARNING TOOLS =====
        elif name == "learn_from_feedback":
            try:
                from tools.learning.contextual_learning import learn_from_feedback
                context = args.get("context", "")
                correct_steps = args.get("correct_steps", [])
                explanation = args.get("explanation", None)
                
                if not context or not correct_steps:
                    return "❌ Context ve correct_steps gerekli."
                
                result = learn_from_feedback(context, correct_steps, explanation)
                
                if result.get("status") == "success":
                    return f"🧠 Öğrendim: {context}\nDoğru adımlar: {', '.join(correct_steps)}"
                else:
                    return f"❌ Öğrenme hatası: {result.get('error', 'Bilinmeyen hata')}"
            except Exception as e:
                return f"❌ Öğrenme hatası: {str(e)}"
        
        elif name == "what_did_i_learn":
            try:
                from tools.learning.contextual_learning import what_did_i_learn
                topic = args.get("topic", None)
                result = what_did_i_learn(topic)
                
                if topic and result.get("found"):
                    pattern = result["pattern"]
                    return f"🧠 {topic} için öğrenilen:\n→ Doğru: {pattern.get('correct_pattern')}\n→ Güven: {pattern.get('confidence', 0)*100:.0f}%"
                elif "patterns" in result:
                    count = len(result["patterns"])
                    stats = result.get("statistics", {})
                    return f"🧠 Toplam {count} kalıp öğrenilmiş.\nKullanım: {stats.get('total_successful_uses', 0)}\nOrt. Güven: {stats.get('average_confidence', 0)*100:.0f}%"
                else:
                    return f"🧠 '{topic}' için öğrenilmiş kalıp yok."
            except Exception as e:
                return f"❌ Öğrenme sorgulama hatası: {str(e)}"
        
        elif name == "forget_learning":
            try:
                from tools.learning.contextual_learning import forget_learning
                context = args.get("context", "")
                if not context:
                    return "❌ Context gerekli."
                
                result = forget_learning(context)
                
                if result.get("status") == "success":
                    return f"🧹 Unuttum: {context}"
                else:
                    return f"❌ '{context}' zaten öğrenilmemiş."
            except Exception as e:
                return f"❌ Unutma hatası: {str(e)}"
        
        # ===== TASK MANAGER TOOLS =====
        elif name == "add_task":
            try:
                from tools.tasks.task_manager import add_task as tm_add_task
                action = args.get("action", "")
                if not action:
                    return "❌ Görev açıklaması (action) gerekli."
                
                deadline = args.get("deadline", None)
                priority = args.get("priority", "medium")
                category = args.get("category", "personal")
                
                result = tm_add_task(action, deadline, priority, category)
                
                if result.get("status") == "success":
                    task = result["task"]
                    deadline_str = f" (Deadline: {deadline})" if deadline else ""
                    return f"📋 Görev eklendi: {action}{deadline_str}"
                else:
                    return f"❌ Görev eklenemedi: {result.get('error', 'Bilinmeyen hata')}"
            except Exception as e:
                return f"❌ Görev ekleme hatası: {str(e)}"
        
        elif name == "complete_task":
            try:
                from tools.tasks.task_manager import complete_task as tm_complete_task
                task_id = args.get("task_id", "")
                if not task_id:
                    return "❌ Görev ID'si gerekli."
                
                result = tm_complete_task(task_id)
                
                if result.get("status") == "success":
                    return f"✅ Görev tamamlandı!"
                else:
                    return f"❌ Görev bulunamadı: {task_id}"
            except Exception as e:
                return f"❌ Görev tamamlama hatası: {str(e)}"
        
        elif name == "list_tasks":
            try:
                from tools.tasks.task_manager import list_tasks as tm_list_tasks
                filter_type = args.get("filter_type", "all")
                result = tm_list_tasks(filter_type)
                
                if result.get("status") == "success":
                    tasks = result["tasks"]
                    
                    if filter_type == "all":
                        active = len(tasks.get("active", []))
                        pending = len(tasks.get("pending", []))
                        completed = len(tasks.get("completed", []))
                        return f"📋 Görevler:\n• Aktif: {active}\n• Bekleyen: {pending}\n• Tamamlanan: {completed}"
                    else:
                        if isinstance(tasks, list):
                            if not tasks:
                                return f"📋 {filter_type} kategorisinde görev yok."
                            task_list = "\n".join([f"• {t.get('action', '?')}" for t in tasks[:5]])
                            return f"📋 {filter_type.capitalize()} görevler:\n{task_list}"
                        return f"📋 {len(tasks)} görev bulundu."
                else:
                    return f"❌ Görev listesi alınamadı."
            except Exception as e:
                return f"❌ Görev listeleme hatası: {str(e)}"
        
        elif name == "get_task_summary":
            try:
                from tools.tasks.task_manager import get_task_summary
                result = get_task_summary()
                
                return f"📋 {result.get('message', 'Görev özeti alınamadı')}"
            except Exception as e:
                return f"❌ Görev özeti hatası: {str(e)}"
        
        elif name == "process_task_from_text":
            try:
                from tools.tasks.task_manager import process_task_from_text
                text = args.get("text", "")
                if not text:
                    return "❌ Metin gerekli."
                
                result = process_task_from_text(text)
                
                if result.get("status") == "success":
                    task = result["task"]
                    deadline_str = f" (Deadline: {task.get('deadline')})" if task.get('deadline') else ""
                    return f"📋 Görev tespit edildi ve eklendi: {task.get('action', '?')}{deadline_str}"
                elif result.get("status") == "no_task":
                    return "ℹ️ Bu cümlede görev tespit edilemedi."
                else:
                    return f"❌ Hata: {result.get('error', 'Bilinmeyen')}"
            except Exception as e:
                return f"❌ Görev çıkarma hatası: {str(e)}"
            
        else:
            return f"Unknown tool: {name}"
    except Exception as e:
        return f"Tool error: {str(e)}"

