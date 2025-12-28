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
        
        # Wayland State
        wayland_process = None
        wayland_buffer = b""
        session_type = os.environ.get('XDG_SESSION_TYPE', 'x11').lower()

        while True:
            try:
                # Cleanup Wayland process if NOT in screen mode
                if state.video_mode != "screen" and wayland_process:
                     try:
                         wayland_process.terminate()
                         await wayland_process.wait()
                     except:
                         pass
                     wayland_process = None
                     wayland_buffer = b""

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
                    # Screen mode - Dual Support (Wayland & X11)
                    
                    if not screen_announced:
                        print(f"{Colors.GREEN}🖥️ Ekran paylaşımı başladı ({session_type}){Colors.RESET}")
                        screen_announced = True

                    img = None

                    # 1. Wayland Strategy: XDG Portal ScreenCast (one-time permission, continuous stream)
                    if "wayland" in session_type:
                        from audio.wayland_capture import get_wayland_capture
                        
                        wayland_cap = get_wayland_capture()
                        
                        # Start session if not already active (shows permission dialog once)
                        if not wayland_cap.session_active:
                            # Check if in cooldown (after failure or starting)
                            if wayland_cap._failed or wayland_cap._starting:
                                # Silent wait during cooldown
                                await asyncio.sleep(2)
                                continue
                            
                            # Only print once at start
                            if not hasattr(wayland_cap, '_dialog_shown'):
                                print(f"{Colors.GREEN}🚀 Wayland ScreenCast başlatılıyor (Lütfen ekran seçin)...{Colors.RESET}")
                                wayland_cap._dialog_shown = True
                            
                            success = await asyncio.to_thread(wayland_cap.start_session)
                            if not success:
                                await asyncio.sleep(5)  # Wait before checking again
                                continue
                        
                        # Capture frame from the stream
                        img = await asyncio.to_thread(wayland_cap.capture_frame)
                        
                        if img is None:
                            wayland_buffer = b""

                    # 2. X11 Strategy: MSS
                    else:
                        try:
                            def grab_screen_x11():
                                import mss
                                with mss.mss() as sct:
                                    monitor = sct.monitors[1]
                                    screenshot = sct.grab(monitor)
                                    return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                            
                            img = await asyncio.to_thread(grab_screen_x11)
                        except Exception as e:
                             print(f"{Colors.YELLOW}⚠️ X11 Capture Hatası: {e}{Colors.RESET}")
                    
                    if img is None:
                         # No frame yet, or waiting for stream
                         await asyncio.sleep(0.01) # Short sleep to yield
                         continue

                    # PiP: Overlay camera feed
                    # Ensure camera is open
                    if cap is None or not cap.isOpened():
                        cap = await asyncio.to_thread(cv2.VideoCapture, 0)

                    if cap and cap.isOpened():
                        ret, cam_frame = await asyncio.to_thread(cap.read)
                        if ret:
                            # Convert camera frame to PIL
                            cam_rgb = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
                            cam_img = Image.fromarray(cam_rgb)
                            
                            # Resize to 20% of screen width
                            pip_width = int(img.width * 0.2)
                            aspect_ratio = cam_img.height / cam_img.width
                            pip_height = int(pip_width * aspect_ratio)
                            cam_img = cam_img.resize((pip_width, pip_height), Image.Resampling.LANCZOS)
                            
                            # Position: Bottom-Right with padding
                            padding = 20
                            x_pos = img.width - pip_width - padding
                            y_pos = img.height - pip_height - padding
                            
                            # Paste camera onto screen
                            img.paste(cam_img, (x_pos, y_pos))
                
                elif state.video_mode == "workspace":
                    # Virtual Workspace mode - capture DISPLAY=:99
                    try:
                        def grab_workspace_screen():
                            import subprocess
                            import tempfile
                            
                            # Use scrot or import to capture from :99
                            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                                temp_path = f.name
                            
                            try:
                                # Try using import (ImageMagick)
                                result = subprocess.run(
                                    ['import', '-display', ':99', '-window', 'root', temp_path],
                                    capture_output=True,
                                    timeout=5
                                )
                                if result.returncode == 0:
                                    img = Image.open(temp_path)
                                    return img.copy()
                            except Exception:
                                pass
                            finally:
                                try:
                                    os.unlink(temp_path)
                                except:
                                    pass
                            
                            return None
                        
                        if not screen_announced:
                            print(f"{Colors.GREEN}🖥️ Sanal ekran paylaşımı başladı (DISPLAY=:99){Colors.RESET}")
                            screen_announced = True
                        
                        img = await asyncio.to_thread(grab_workspace_screen)
                        
                        if img is None:
                            print(f"{Colors.YELLOW}🖥️ Sanal ekran yakalanamadı{Colors.RESET}")
                            await asyncio.sleep(FRAME_INTERVAL)
                            continue
                            
                    except Exception as e:
                        print(f"{Colors.YELLOW}🖥️ Workspace capture hatası: {e}{Colors.RESET}")
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
                
                if state.video_mode != "screen":
                     await asyncio.sleep(FRAME_INTERVAL)
                else:
                     # For screen stream, we want low latency, small sleep
                     await asyncio.sleep(0.01)
                
            except Exception as e:
                print(f"{Colors.DIM}📷 Frame hatası (Ana Döngü): {e}{Colors.RESET}")
                await asyncio.sleep(FRAME_INTERVAL)
        
        if cap:
            cap.release()
            
    except ImportError:
        print(f"{Colors.YELLOW}📷 opencv-python yüklü değil{Colors.RESET}")
    except Exception as e:
        print(f"{Colors.YELLOW}📷 Görüntü hatası: {e}{Colors.RESET}")
