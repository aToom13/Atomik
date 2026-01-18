"""
Simple HTTP server for serving VRM avatar content.
This bypasses WebKitGTK's file:// restrictions for Three.js.
"""
import http.server
import socketserver
import threading
import os

# Server configuration
PORT = 8765
UI_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(UI_DIR)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that serves files from project root"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PROJECT_ROOT, **kwargs)
    
    def log_message(self, format, *args):
        # Suppress logging
        pass
    
    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()


class AvatarServer:
    """Manages the local HTTP server for avatar content"""
    
    _instance = None
    _server = None
    _thread = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def start(self):
        """Start the HTTP server in a background thread"""
        if self._server is not None:
            return self.get_url()
        
        try:
            # Enable port reuse BEFORE creating the server
            socketserver.TCPServer.allow_reuse_address = True
            self._server = socketserver.TCPServer(("127.0.0.1", PORT), QuietHandler)
            
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            
            print(f"[Avatar] 🌐 HTTP server started on http://127.0.0.1:{PORT}")
            return self.get_url()
        except OSError as e:
            if "Address already in use" in str(e) or "Adres zaten" in str(e):
                print(f"[Avatar] ⚠️ Port {PORT} already in use, assuming server running")
                return self.get_url()
            raise
    
    def stop(self):
        """Stop the HTTP server"""
        if self._server:
            self._server.shutdown()
            self._server = None
            self._thread = None
            print("[Avatar] 🔴 HTTP server stopped")
    
    def get_url(self):
        """Get the URL for the VRM avatar page"""
        return f"http://127.0.0.1:{PORT}/ui/avatar_vrm.html"


def start_server():
    """Convenience function to start the server"""
    return AvatarServer.get_instance().start()


def stop_server():
    """Convenience function to stop the server"""
    AvatarServer.get_instance().stop()


if __name__ == "__main__":
    # Test the server
    url = start_server()
    print(f"Server running at: {url}")
    print("Press Ctrl+C to stop")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        stop_server()
