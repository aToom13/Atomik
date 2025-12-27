import json
import urllib.request
import urllib.error
import websocket
import time
from langchain_core.tools import tool
try:
    from config import config
except ImportError:
    try:
        from AtomBase.config import config
    except ImportError:
         # Fallback
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from AtomBase.config import config

try:
    from utils.logger import get_logger
except ImportError:
    from AtomBase.utils.logger import get_logger

logger = get_logger()

def get_debug_url(port=9222):
    """Bulunan ilk sayfanın WebSocket URL'ini döndürür"""
    try:
        url = f"http://localhost:{port}/json"
        with urllib.request.urlopen(url, timeout=2) as response:
            data = json.loads(response.read().decode())
            # Tipi 'page' olan ilk sekmeyi bul
            for page in data:
                if page.get("type") == "page" and "webSocketDebuggerUrl" in page:
                    return page["webSocketDebuggerUrl"]
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        # 404 veya diğer hatalarda, doğrudan WebSocket bağlantılarını dene
        logger.warning(f"Connection Error ({e}) (Port {port}), waiting and trying direct WebSocket candidates...")
        time.sleep(1) 
        
        candidates = [
            f"ws://127.0.0.1:{port}",           # Zen/Firefox varsayılanı (tahmin)
            f"ws://127.0.0.1:{port}/session",   # BiDi standardı
            f"ws://localhost:{port}",
            f"ws://localhost:{port}/session"
        ]
        
        for url in candidates:
            try:
                # Test connection (timeout kısa tutulmalı)
                ws = websocket.create_connection(url, timeout=1, suppress_origin=True)
                ws.close()
                logger.info(f"✅ Debugger connection found at: {url}")
                return url
            except Exception:
                continue
                
        return None # Hiçbiri çalışmadı

def extract_dom_elements(ws_url):
    """WebSocket ile bağlanıp DOM elemanlarını çeker (BiDi ve CDP desteği)"""
    ws = None
    try:
        ws = websocket.create_connection(ws_url, timeout=5, suppress_origin=True)
        
        # 1. BiDi Session Başlat (Eğer ws_url /session ile bitiyorsa)
        if ws_url.endswith("/session"):
            # Önce varsa eski mesajları temizle (flush)
            ws.settimeout(0.1)
            try:
                while True: ws.recv()
            except: pass
            ws.settimeout(5)

            # A. Session.new
            ws.send(json.dumps({
                "id": 100,
                "method": "session.new",
                "params": {"capabilities": {}}
            }))
            
            # Yanıtı BEKLE (ID 100) - Kritik Düzeltme!
            session_ok = False
            for _ in range(5):
                try:
                    chunk = json.loads(ws.recv())
                    if chunk.get("id") == 100:
                        if "error" in chunk:
                            logger.error(f"Session.new error: {chunk}")
                        else:
                            session_ok = True
                            # logger.info(f"Session created: {chunk}")
                        break
                except: pass
            
            if not session_ok:
                logger.warning("Session.new yanıtı alınamadı (Timeout). Yine de devam ediyoruz...")

            # B. Contextleri Listele (browsingContext.getTree) - RETRY MEKANİZMASI
            context_id = None
            for attempt in range(3):
                ws.send(json.dumps({
                    "id": 101,
                    "method": "browsingContext.getTree",
                    "params": {}
                }))
                
                try:
                    chunk = json.loads(ws.recv())
                    if "result" in chunk and "contexts" in chunk["result"]:
                        contexts = chunk["result"]["contexts"]
                        if contexts:
                            context_id = contexts[0]["context"]
                            break
                    
                    if "error" in chunk:
                        logger.warning(f"BiDi Attempt {attempt+1} Error: {chunk}")
                        time.sleep(1)
                except Exception as e:
                    logger.warning(f"BiDi Attempt {attempt+1} Exception: {e}")
            
            if not context_id:
                logger.error("BiDi: Context ID bulunamadı (Tüm denemeler başarısız).")
                return []
                
            logger.info(f"BiDi Context ID: {context_id}")

            # C. JS Çalıştır (script.evaluate)
            js_code = """
            (function() {
                // Ekran offset'lerini hesapla (Tarayıcı penceresi + toolbar)
                const offsetX = window.screenX + (window.outerWidth - window.innerWidth) / 2;
                const offsetY = window.screenY + (window.outerHeight - window.innerHeight);
                
                const elements = document.querySelectorAll('button, a, input, [role="button"], [role="link"], [role="menuitem"]');
                const results = [];
                elements.forEach((el) => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        const style = window.getComputedStyle(el);
                        if (style.display !== 'none' && style.visibility !== 'hidden') {
                            let text = el.innerText || el.value || el.getAttribute('aria-label') || "";
                            text = text.trim(); 
                            // Ekran koordinatlarına çevir
                            results.push({
                                tag: el.tagName.toLowerCase(),
                                text: text,
                                x: Math.round(rect.left + rect.width / 2 + offsetX),
                                y: Math.round(rect.top + rect.height / 2 + offsetY),
                                id: el.id
                            });
                        }
                    }
                });
                return JSON.stringify(results);
            })()
            """
            
            ws.send(json.dumps({
                "id": 102,
                "method": "script.evaluate",
                "params": {
                    "expression": js_code,
                    "target": {"context": context_id},
                    "awaitPromise": True,
                    "resultOwnership": "root" 
                }
            }))
            
            # Yanıtı bekle (Loop ile)
            for _ in range(10):
                try:
                    chunk = json.loads(ws.recv())
                    if chunk.get("id") == 102:
                        if "result" in chunk and "result" in chunk["result"]:
                            res_val = chunk["result"]["result"]
                            if res_val["type"] == "string":
                                return json.loads(res_val["value"])
                        break 
                except: pass
            
            return []

        # 2. CDP Fallback
        else:
            js_code = """
            (function() {
                try {
                // Ekran offset'lerini hesapla
                const offsetX = window.screenX + (window.outerWidth - window.innerWidth) / 2;
                const offsetY = window.screenY + (window.outerHeight - window.innerHeight);
                
                const elements = document.querySelectorAll('button, a, input, [role="button"], [role="link"], [role="menuitem"]');
                const results = [];
                elements.forEach((el) => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        const style = window.getComputedStyle(el);
                        if (style.display !== 'none' && style.visibility !== 'hidden') {
                            let text = el.innerText || el.value || el.getAttribute('aria-label') || "";
                            text = text.trim(); 
                            results.push({
                                tag: el.tagName.toLowerCase(),
                                text: text,
                                x: Math.round(rect.left + rect.width / 2 + offsetX),
                                y: Math.round(rect.top + rect.height / 2 + offsetY),
                                id: el.id
                            });
                        }
                    }
                });
                return JSON.stringify(results);
                } catch(e) { return JSON.stringify([]); }
            })()
            """
            
            # CDP Komutu: Runtime.evaluate
            request = {
                "id": 200,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": js_code,
                    "returnByValue": True
                }
            }
            
            ws.send(json.dumps(request))
            response = ws.recv()
            
            result_json = json.loads(response)
            if "result" in result_json and "result" in result_json["result"]:
                value = result_json["result"]["result"]["value"]
                return json.loads(value)
                
            return []
            
    except Exception as e:
        logger.error(f"DOM extraction error: {e}")
        return []
    finally:
        if ws:
            # Session'ı kapat (Maximum sessions hatasını önlemek için)
            try:
                ws.send(json.dumps({"id": 999, "method": "session.end", "params": {}}))
                ws.settimeout(0.5)
                ws.recv()
            except: pass
            ws.close()
        
    return []

@tool
def inspect_web_page(port: int = 9222) -> str:
    """
    Aktif web sayfasının DOM yapısını (tıklanabilir öğeler) analiz eder.
    Args:
        port: Tarayıcının debug portu (varsayılan 9222).
    Returns:
        JSON formatında element listesi (tag, text, x, y).
    """
    # Sayfanın tam yüklenmesi için bekle
    time.sleep(5)
    
    ws_url = get_debug_url(port)
    if not ws_url:
        return f"❌ Bağlantı hatası: localhost:{port} üzerinde açık tarayıcı bulunamadı. Lütfen tarayıcının '--remote-debugging-port={port}' ile başladığından emin olun."
    
    elements = extract_dom_elements(ws_url)
    if not elements:
        return "⚠️ Sayfada tıklanabilir öğe bulunamadı veya erişilemedi."
    
    # Viewport yüksekliği (tahmini - toolbar dahil)
    VIEWPORT_HEIGHT = 900
    
    # Öğeleri görünür/görünmez olarak ayır
    visible_elements = []
    scrolled_elements = []
    
    for el in elements:
        if el['text'] or el['id']:
            if 0 < el['y'] < VIEWPORT_HEIGHT:
                visible_elements.append(el)
            elif el['y'] >= VIEWPORT_HEIGHT:
                scrolled_elements.append(el)
    
    # Özet oluştur
    summary = f"🔍 Bulunan Öğeler: {len(visible_elements)} görünür, {len(scrolled_elements)} scroll gerektirir\n\n"
    
    summary += "📍 GÖRÜNÜR ALAN (Tıklanabilir):\n"
    for el in visible_elements:
        summary += f"- [{el['tag']}] '{el['text']}' (x={el['x']}, y={el['y']})\n"
    
    if scrolled_elements:
        summary += f"\n📜 SCROLL GEREKLİ ({len(scrolled_elements)} öğe aşağıda):\n"
        for el in scrolled_elements[:10]:  # İlk 10 tanesi
            summary += f"- [AŞAĞIDA] [{el['tag']}] '{el['text']}' (y={el['y']})\n"
        if len(scrolled_elements) > 10:
            summary += f"... ve {len(scrolled_elements) - 10} öğe daha.\n"
    
    return summary
