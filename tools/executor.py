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

# ===== NEW: Unified Memory & Tools =====
try:
    from tools.memory.unified import manage_memory, query_memory
    from tools.dev.quality import verify_code_quality
    from tools.system.virtual_input import virtual_input
    UNIFIED_TOOLS_AVAILABLE = True
except ImportError as e:
    print(f"{Colors.RED}Unified tools import error: {e}{Colors.RESET}")
    manage_memory = None
    UNIFIED_TOOLS_AVAILABLE = False

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
    from AtomBase.utils.logger import get_logger
    from tools.dev.coding import delegate_coding, save_generated_code
    # Memory and Visual Memory imports removed - replaced by unified tools

    logger = get_logger()
    from tools.web.web import visit_webpage
    from tools.web.youtube import get_youtube_content
    ATOMBASE_AVAILABLE = True
    CODING_AVAILABLE = True
    MEMORY_AVAILABLE = UNIFIED_TOOLS_AVAILABLE # Redirect to unified
    WEATHER_AVAILABLE = True
    CAMERA_AVAILABLE = True
    VISUAL_MEMORY_AVAILABLE = UNIFIED_TOOLS_AVAILABLE # Redirect to unified
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
        elif name == "visit_webpage":
            return visit_webpage(args.get("url"))
            
        elif name == "analyze_youtube":
            url = args.get("url")
            query = args.get("query")
            
            # İçeriği çek
            data = get_youtube_content(url, query)
            
            if "error" in data:
                return f"❌ YouTube Analiz Hatası: {data['error']}"
                
            # Prompt'u yükle
            try:
                with open("AtomBase/prompts/youtube_analysis.txt", "r") as f:
                    system_prompt = f.read()
            except:
                return "❌ Prompt dosyası (youtube_analysis.txt) bulunamadı."
                
            # Modele gönderilecek içerik
            user_content = f"""
BAŞLIK: {data['metadata'].get('title')}
KANAL: {data['metadata'].get('author')}
AÇIKLAMA: {data['metadata'].get('description')}
TRANSKRIPT:
{data['transcript_preview']} (Tamamı analiz ediliyor...)

KULLANICI SORUSU: {query if query else 'Genel Analiz İsteği'}
"""
            # Burada normalde LLM call yapılmalı ama executor sadece string dönüyor.
            # Bu yüzden veriyi döndüreceğiz, model bunu yorumlayacak.
            # VEYA direkt burada LLM çağrısı yapıp sonucu döndürebiliriz (DAHA İYİ).
            # Ancak şimdilik veriyi zenginleştirip modele "Ben bunu buldum, sen analiz et" diyeceğiz.
            
            return f"""🎬 YOUTUBE VİDEO VERİSİ (Analiz Et):

BAŞLIK: {data['metadata'].get('title')}
KANAL: {data['metadata'].get('author')}
SÜRE: {data['metadata'].get('duration')}s
İZLENME: {data['metadata'].get('views')}

AÇIKLAMA:
{data['metadata'].get('description')[:500]}...

ALTYAZI (TRANSKRIPT):
{data['full_transcript'][:15000]} 

(NOT: Altyazı çok uzunsa kırpılmış olabilir. Yukarıdaki metni kullanarak kullanıcının '{query}' sorusunu cevapla veya özet geç.)"""
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
             return "Deprecated. Use run_terminal_command('neofetch')."
        
        # ===== NEW: Unified Memory Tools =====
        elif name == "manage_memory":
            if UNIFIED_TOOLS_AVAILABLE:
                return manage_memory(args["action"], args["category"], args.get("key"), args.get("content"))
            return "Unified tools module not available"
            
        elif name == "query_memory":
            if UNIFIED_TOOLS_AVAILABLE:
                return query_memory(args["query"], args.get("filter_type", "all"), args.get("time_range"))
            return "Unified tools module not available"
            
        elif name == "verify_code_quality":
            if UNIFIED_TOOLS_AVAILABLE:
                return verify_code_quality(args["filepath"], args.get("actions"))
            return "Unified tools module not available"
            
        elif name == "virtual_input":
             if UNIFIED_TOOLS_AVAILABLE:
                return virtual_input(args["action"], args.get("x"), args.get("y"), args.get("text"), args.get("window"))
             return "Unified tools module not available"
             
        # Redirect deprecated memory tools
        elif name in ["save_context", "remember_this", "log_mood", "update_preference", "add_project", "save_visual_observation"]:
            return "⚠️ Bu araç birleştirildi. Lütfen 'manage_memory' aracını kullanın."
            
        elif name in ["get_context_info", "recall_memory", "get_recent_memories", "get_visual_history", "search_chat_history"]:
            return "⚠️ Bu araç birleştirildi. Lütfen 'query_memory' aracını kullanın."

        # Camera tool removed - frames are sent automatically via VAD in audio/video.py
        # Exit tool
        elif name == "exit_app":
            state.exit_requested = True
            return "Güle güle! Seninle sohbet etmek güzeldi. Tekrar görüşmek üzere!"
        # Visual Memory Tools
            return "Görsel hafıza kullanılamıyor"
        # Redirect deprecated visual memory
        # (Handled above in consolidated block)

        # Screen Sharing Tools
        elif name == "share_screen":
            state.video_mode = "screen"
            return "🖥️ Tamam! Kamerayı kapatıp ekranını izlemeye başlıyorum. 'Ekranı bırakabilirsin' dediğinde geri kameraya döneceğim."
        elif name == "stop_screen_share":
            state.video_mode = "camera"
            return "📷 Ekran paylaşımı durduruldu. Kameraya geri dönüyorum!"
        elif name == "share_workspace_screen":
            # Clear stale frame from previous mode to prevent 1008 error
            state.latest_image_payload = None
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
            return "⚠️ 'find_ui_element' birleştirildi. Lütfen 'see_screen(find=...)' kullanın."

        
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
                    headers = {"User-Agent": "Mozilla/5.0"}
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
        # ===== RAG MEMORY TOOLS (Deprecated) =====
        elif name in ["remember_this", "recall_memory", "get_recent_memories"]:
             return "⚠️ Bu araç birleştirildi. Lütfen 'manage_memory' veya 'query_memory' aracını kullanın."

        
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
        # ===== SESSION HISTORY TOOLS (Deprecated) =====
        elif name in ["search_chat_history", "get_chat_stats"]:
            return "⚠️ Bu araç birleştirildi. Lütfen 'query_memory' aracını kullanın."

        
        # ===== CODE QUALITY TOOLS =====
        # ===== CODE QUALITY TOOLS (Deprecated) =====
        elif name in ["run_linter", "format_code", "run_tests"]:
            return "⚠️ Bu araç birleştirildi. Lütfen 'verify_code_quality' aracını kullanın."


        
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
        
        elif name == "delegate_coding":
            try:
                from tools.dev.coding import delegate_coding
                prompt = args.get("prompt", "")
                context = args.get("context", "")
                return delegate_coding(prompt, context)
            except Exception as e:
                return f"❌ Kodlama delegasyon hatası: {str(e)}"
        
        elif name == "inspect_web_page":
            try:
                from tools.web.web_inspector import inspect_web_page
                port = args.get("port", 9222)
                return inspect_web_page.invoke({"port": port})
            except Exception as e:
                return f"❌ DOM analiz hatası: {str(e)}"

        elif name == "get_weather":
            # Basit mock implementation
            city = args.get("city", "İstanbul")
            return f"🌤️ {city}: 22°C, Açık (Mock Data)"
        

        
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
        
        elif name == "view_captured_window":
            try:
                from tools.system.workspace import view_captured_window
                return view_captured_window()
            except ImportError:
                 return "❌ 'view_captured_window' henüz implemente edilmedi."
            except Exception as e:
                return f"❌ Pencere görüntüleme hatası: {str(e)}"
        
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
        
        # ===== VIRTUAL INPUT TOOLS (Deprecated) =====
        elif name in ["type_in_workspace", "send_key_in_workspace", "click_in_workspace", "focus_window_in_workspace"]:
            return "⚠️ Bu araç birleştirildi. Lütfen 'virtual_input' aracını kullanın."

        
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

