"""
Atomik GTK Avatar Application
Main GTK4 + Adwaita window with Live2D avatar via WebKitGTK WebView
"""
import os
import sys
import json
import asyncio
import threading
from typing import Optional

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
gi.require_version('Gdk', '4.0')

# Try WebKit - may need: sudo pacman -S webkit2gtk-4.1
try:
    gi.require_version('WebKit', '6.0')
    from gi.repository import WebKit
    WEBKIT_AVAILABLE = True
except:
    try:
        gi.require_version('WebKit2', '4.1')
        from gi.repository import WebKit2 as WebKit
        WEBKIT_AVAILABLE = True
    except:
        WEBKIT_AVAILABLE = False
        print("[Avatar] ⚠️ WebKitGTK not found. Install: sudo pacman -S webkit2gtk-4.1")

from gi.repository import Gtk, Adw, Gdk, GLib, Gio


# Paths
UI_DIR = os.path.dirname(os.path.abspath(__file__))
AVATAR_HTML = os.path.join(UI_DIR, "avatar.html")  # Live2D avatar (VRM not working yet)
PROJECT_ROOT = os.path.dirname(UI_DIR)
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")


class AvatarWebView(Gtk.Box):
    """
    WebView container for Live2D avatar.
    Uses WebKitGTK to render avatar.html with Live2D Web SDK.
    """
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        
        self.webview = None
        self._ready = False
        
        if not WEBKIT_AVAILABLE:
            # Fallback: show error message
            label = Gtk.Label(label="❌ WebKitGTK not installed\n\nRun: sudo pacman -S webkit2gtk-4.1")
            label.set_justify(Gtk.Justification.CENTER)
            self.append(label)
            return
        
        # Create WebView with disabled sandbox (fixes bwrap permission error)
        # Use NetworkSession to control web process settings
        try:
            # WebKit 6.0 style
            network_session = WebKit.NetworkSession.new_ephemeral()
            web_context = WebKit.WebContext.new()
            self.webview = WebKit.WebView.new_with_context(web_context)
        except:
            # Fallback for older WebKit versions
            self.webview = WebKit.WebView()
        
        self.webview.set_hexpand(True)
        self.webview.set_vexpand(True)
        
        # Enable transparency
        try:
            self.webview.set_background_color(Gdk.RGBA(0, 0, 0, 0))
        except:
            pass
        
        # Settings
        settings = self.webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_webgl(True)
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_allow_universal_access_from_file_urls(True)
        
        # Disable sandbox for local file access (fixes bwrap permission denied)
        try:
            settings.set_property("enable-sandbox", False)
        except:
            pass
        
        # Connect load signal
        self.webview.connect("load-changed", self._on_load_changed)
        
        self.append(self.webview)
        
        # Load avatar HTML
        self._load_avatar()
    
    def _load_avatar(self):
        """Load avatar HTML via HTTP server for VRM support"""
        # Start HTTP server for VRM content
        try:
            from ui.avatar_server import start_server
            avatar_url = start_server()
            self.webview.load_uri(avatar_url)
            print(f"[Avatar] Loading VRM: {avatar_url}")
        except Exception as e:
            print(f"[Avatar] ⚠️ HTTP server failed: {e}, falling back to Live2D")
            # Fallback to Live2D
            live2d_html = os.path.join(UI_DIR, "avatar.html")
            if os.path.exists(live2d_html):
                self.webview.load_uri(f"file://{live2d_html}")
                print(f"[Avatar] Loading Live2D fallback")
    
    def _on_load_changed(self, webview, event):
        """Handle page load events"""
        if event == WebKit.LoadEvent.FINISHED:
            self._ready = True
            print("[Avatar] ✅ WebView loaded")
    
    def send_command(self, command: str, data=None):
        """Send command to avatar JavaScript"""
        if not self._ready or not self.webview:
            return
        
        if data is None:
            js = f"window.avatarAPI?.{command}()"
        else:
            js = f"window.avatarAPI?.{command}({json.dumps(data)})"
        
        self.webview.evaluate_javascript(js, -1, None, None, None, None, None)
    
    def set_mouth(self, value: float):
        """Set mouth openness (0-1)"""
        self.send_command("setMouth", value)
    
    def play_gesture(self, gesture: str, intensity: float = 0.7):
        """Trigger a gesture animation"""
        if not self._ready or not self.webview:
            return
        js = f"window.avatarAPI?.gesture('{gesture}', {intensity})"
        self.webview.evaluate_javascript(js, -1, None, None, None, None, None)


class AvatarWindow(Adw.ApplicationWindow):
    """
    Main avatar window with GTK4/Adwaita styling.
    """
    
    def __init__(self, app: Adw.Application, audio_loop=None):
        super().__init__(application=app)
        
        self.audio_loop = audio_loop
        
        # Setup window
        self.set_title("Atomik Avatar")
        self.set_default_size(450, 550)
        
        # Build UI
        self._build_ui()
        
        # Connect audio callbacks if available
        if self.audio_loop:
            self.audio_loop.on_audio_output = self._on_audio_output
            self.audio_loop.on_transcription = self._on_transcription
        
        # Setup gesture callback for AI body control
        try:
            from tools.gesture_tool import set_gesture_callback
            set_gesture_callback(self._on_gesture)
        except ImportError:
            print("[Avatar] ⚠️ gesture_tool not found")
    
    def _build_ui(self):
        """Build the UI hierarchy"""
        # Main container
        overlay = Gtk.Overlay()
        self.set_content(overlay)
        
        # Avatar WebView (fills window)
        self.avatar = AvatarWebView()
        overlay.set_child(self.avatar)
        
        # Status label (bottom overlay)
        self.status_label = Gtk.Label(label="")
        self.status_label.add_css_class("avatar-status")
        self.status_label.set_halign(Gtk.Align.CENTER)
        self.status_label.set_valign(Gtk.Align.END)
        self.status_label.set_margin_bottom(20)
        overlay.add_overlay(self.status_label)
        
        # Apply CSS
        self._apply_css()
    
    def _apply_css(self):
        """Apply custom styling"""
        css = b"""
        window {
            background: #1a1a2e;
        }
        
        .avatar-status {
            background: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def _on_audio_output(self, level: float):
        """Callback from AudioLoop - audio output level for lip sync"""
        def update():
            self.avatar.set_mouth(level)
            return False
        GLib.idle_add(update)
    
    def _on_transcription(self, text: str, is_user: bool):
        """Callback from AudioLoop - transcription text"""
        def update():
            prefix = "🎤 " if is_user else "🤖 "
            display_text = text[:50] + "..." if len(text) > 50 else text
            self.status_label.set_text(f"{prefix}{display_text}")
            return False
        GLib.idle_add(update)
    
    def _on_gesture(self, gesture: str, intensity: float = 0.7):
        """Callback from AI - trigger avatar gesture"""
        def update():
            self.avatar.play_gesture(gesture, intensity)
            return False
        GLib.idle_add(update)


class AvatarApp(Adw.Application):
    """Main GTK Application"""
    
    def __init__(self, audio_loop=None):
        super().__init__(
            application_id="com.atomik.avatar",
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.audio_loop = audio_loop
        self.window = None
    
    def do_activate(self):
        """Called when app is activated"""
        if not self.window:
            self.window = AvatarWindow(self, self.audio_loop)
        self.window.present()


def run_avatar_mode(offline: bool = False):
    """
    Main entry point for avatar mode.
    Runs GTK main loop with AudioLoop in background thread.
    """
    print("[Avatar] 🎭 Starting Avatar Mode...")
    
    # Import audio loop
    if offline:
        from audio.local_loop import LocalAudioLoop
        audio_loop = LocalAudioLoop()
    else:
        from audio import AudioLoop
        audio_loop = AudioLoop()
    
    # Create GTK app with audio loop reference
    app = AvatarApp(audio_loop)
    
    # Run audio loop in background thread
    def run_audio():
        asyncio.run(audio_loop.run())
    
    audio_thread = threading.Thread(target=run_audio, daemon=True)
    audio_thread.start()
    
    # Run GTK main loop (blocks until window closes)
    exit_code = app.run(None)
    
    print("[Avatar] 👋 Avatar mode ended")
    return exit_code


def main():
    """Direct run for testing (no audio)"""
    print("[Avatar] 🎭 Testing Avatar Window (no audio)...")
    app = AvatarApp(audio_loop=None)
    app.run(None)


if __name__ == "__main__":
    main()
