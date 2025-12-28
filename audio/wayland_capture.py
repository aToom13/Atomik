"""
Wayland Screen Capture using XDG Desktop Portal ScreenCast
Spawns a persistent subprocess using system Python to keep the portal session alive.
"""

import subprocess
import os
import time
from PIL import Image

TOOLS_DIR = os.path.join(os.path.dirname(__file__), '..', 'tools')
PORTAL_SERVICE = os.path.join(TOOLS_DIR, 'portal_service.py')
NODE_FILE = "/tmp/atomik_screencast_node"
PID_FILE = "/tmp/atomik_screencast.pid"
TEMP_FRAME = "/dev/shm/atomik_portal_frame.jpg"

class WaylandScreenCapture:
    """
    Manages XDG Portal ScreenCast session for Wayland screen capture.
    """
    
    def __init__(self):
        self.node_id = None
        self.session_active = False
        self._failed = False
        self._starting = False
        self._portal_process = None
        self._last_dialog_time = 0
        
    def _check_existing_session(self) -> bool:
        """Check if a working session already exists."""
        if os.path.exists(NODE_FILE) and os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)  # Check if process exists
                with open(NODE_FILE, 'r') as f:
                    self.node_id = int(f.read().strip())
                self.session_active = True
                return True
            except:
                pass
        return False
        
    def start_session(self) -> bool:
        """Start portal session via persistent subprocess."""
        # Already active?
        if self.session_active and self.node_id:
            return True
            
        # Check for existing session
        if self._check_existing_session():
            return True
            
        # Already starting or failed?
        if self._starting:
            return False
            
        # Rate limit dialog attempts (wait 30s between attempts)
        if self._failed and (time.time() - self._last_dialog_time) < 30:
            return False
            
        self._starting = True
        self._last_dialog_time = time.time()
        
        # Clean up old files
        for f in [NODE_FILE, PID_FILE]:
            if os.path.exists(f):
                try:
                    os.unlink(f)
                except:
                    pass
        
        try:
            # Start portal service - it will show dialog and stay running
            self._portal_process = subprocess.Popen(
                ['/usr/bin/python3', PORTAL_SERVICE, 'start'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True  # Detach from parent
            )
            
            # Wait for node file (max 30 seconds)
            for i in range(60):
                if os.path.exists(NODE_FILE):
                    try:
                        with open(NODE_FILE, 'r') as f:
                            self.node_id = int(f.read().strip())
                        self.session_active = True
                        self._starting = False
                        self._failed = False
                        print(f"✅ Wayland ScreenCast Node: {self.node_id}")
                        return True
                    except:
                        pass
                        
                # Check if process died
                if self._portal_process.poll() is not None:
                    break
                    
                time.sleep(0.5)
                
            # Timeout or process died
            self._failed = True
            self._starting = False
            return False
                
        except Exception as e:
            print(f"❌ Portal hatası: {e}")
            self._failed = True
            self._starting = False
            return False
            
    def capture_frame(self) -> Image.Image | None:
        """Capture a single frame from the PipeWire stream."""
        if not self.session_active or self.node_id is None:
            return None
            
        try:
            result = subprocess.run(
                [
                    'gst-launch-1.0', '-q',
                    'pipewiresrc', f'path={self.node_id}', 'num-buffers=1', '!',
                    'videoconvert', '!',
                    'jpegenc', '!',
                    'filesink', f'location={TEMP_FRAME}'
                ],
                capture_output=True,
                timeout=2
            )
            
            if result.returncode == 0 and os.path.exists(TEMP_FRAME):
                img = Image.open(TEMP_FRAME)
                img.load()
                try:
                    os.unlink(TEMP_FRAME)
                except:
                    pass
                return img
            else:
                stderr = result.stderr.decode()
                if "target not found" in stderr or "node" in stderr.lower():
                    # Stream ended, need new session
                    self.session_active = False
                    self.node_id = None
                    self._failed = False  # Allow retry
                
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            pass
            
        return None
        
    def stop(self):
        """Stop the screen cast session."""
        self.session_active = False
        self.node_id = None
        self._failed = False
        self._starting = False
        
        try:
            subprocess.run(['/usr/bin/python3', PORTAL_SERVICE, 'stop'], timeout=5)
        except:
            pass


# Global instance
_capture = None

def get_wayland_capture() -> WaylandScreenCapture:
    """Get or create the global WaylandScreenCapture instance."""
    global _capture
    if _capture is None:
        _capture = WaylandScreenCapture()
    return _capture
