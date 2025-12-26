"""
Video Capture Module - Camera and Screen capture
"""
import asyncio
import io
import os
import sys

# Ensure project root is in path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from PIL import Image
from core import state, FRAME_INTERVAL
from core.colors import Colors


async def capture_frames():
    """Background task to continuously capture camera/screen frames"""
    print(f"{Colors.GREEN}📷 Görüntü yakalama başlatılıyor...{Colors.RESET}")
    
    try:
        import cv2
        
        cap = None
        screen_announced = False
        
        while True:
            try:
                if state.video_mode == "camera":
                    # Camera mode
                    screen_announced = False
                    if cap is None or not cap.isOpened():
                        cap = await asyncio.to_thread(cv2.VideoCapture, 0)
                        if cap.isOpened():
                            print(f"{Colors.GREEN}📷 Kamera hazır (her {FRAME_INTERVAL}s frame){Colors.RESET}")
                        else:
                            await asyncio.sleep(FRAME_INTERVAL)
                            continue
                    
                    ret, frame = await asyncio.to_thread(cap.read)
                    if not ret:
                        await asyncio.sleep(FRAME_INTERVAL)
                        continue
                    
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    
                elif state.video_mode == "screen":
                    # Screen mode using mss
                    try:
                        def grab_screen():
                            import mss
                            with mss.mss() as sct:
                                monitor = sct.monitors[1]
                                screenshot = sct.grab(monitor)
                                return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                        
                        if not screen_announced:
                            print(f"{Colors.GREEN}🖥️ Ekran paylaşımı başladı{Colors.RESET}")
                            screen_announced = True
                        
                        img = await asyncio.to_thread(grab_screen)
                        
                        # Release camera if switching to screen
                        if cap is not None:
                            cap.release()
                            cap = None
                            
                    except ImportError:
                        print(f"{Colors.YELLOW}🖥️ mss yüklü değil, pip install mss{Colors.RESET}")
                        state.video_mode = "camera"
                        await asyncio.sleep(FRAME_INTERVAL)
                        continue
                else:
                    await asyncio.sleep(FRAME_INTERVAL)
                    continue
                
                # Convert to JPEG
                img.thumbnail([1536, 1536])
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=90)
                buffer.seek(0)
                
                state.latest_image_payload = {
                    "mime_type": "image/jpeg",
                    "data": buffer.getvalue()
                }
                
                await asyncio.sleep(FRAME_INTERVAL)
                
            except Exception as e:
                print(f"{Colors.DIM}📷 Frame hatası: {e}{Colors.RESET}")
                await asyncio.sleep(FRAME_INTERVAL)
        
        if cap:
            cap.release()
            
    except ImportError:
        print(f"{Colors.YELLOW}📷 opencv-python yüklü değil{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.YELLOW}📷 Görüntü hatası: {e}{Colors.RESET}")
