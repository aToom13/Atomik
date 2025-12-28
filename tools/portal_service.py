#!/usr/bin/env python3
"""
XDG Desktop Portal ScreenCast Service for Wayland
Uses GLib mainloop to properly handle portal dialogs.
"""

import sys
import os
import time
import signal

# Ensure system packages are available
sys.path.insert(0, '/usr/lib/python3/dist-packages')

NODE_FILE = "/tmp/atomik_screencast_node"
PID_FILE = "/tmp/atomik_screencast.pid"

try:
    import gi
    gi.require_version('Gtk', '4.0')
    from gi.repository import GLib, Gio, Gtk
    HAS_GTK = True
except:
    try:
        gi.require_version('Gtk', '3.0')
        from gi.repository import GLib, Gio, Gtk
        HAS_GTK = True
    except:
        HAS_GTK = False


class PortalScreenCast:
    def __init__(self):
        self.session_handle = None
        self.node_id = None
        self.loop = None
        self.bus = None
        self.portal = None
        
    def start(self):
        """Start screen cast session via XDG Portal."""
        if not HAS_GTK:
            print("❌ GTK not available")
            return False
            
        # Save PID
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        
        self.loop = GLib.MainLoop()
        
        # Setup signal handlers
        def on_signal(signum, frame):
            self.cleanup()
            sys.exit(0)
        signal.signal(signal.SIGTERM, on_signal)
        signal.signal(signal.SIGINT, on_signal)
        
        try:
            # Connect to session bus
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            
            # Get ScreenCast portal
            self.portal = Gio.DBusProxy.new_sync(
                self.bus,
                Gio.DBusProxyFlags.NONE,
                None,
                'org.freedesktop.portal.Desktop',
                '/org/freedesktop/portal/desktop',
                'org.freedesktop.portal.ScreenCast',
                None
            )
            
            # Create unique token
            token = f"atomik_{os.getpid()}_{int(time.time())}"
            
            # Subscribe to Response signal
            self.bus.signal_subscribe(
                'org.freedesktop.portal.Desktop',
                'org.freedesktop.portal.Request',
                'Response',
                None,
                None,
                Gio.DBusSignalFlags.NO_MATCH_RULE,
                self._on_response,
                None
            )
            
            # Step 1: CreateSession
            self.portal.call_sync(
                'CreateSession',
                GLib.Variant('(a{sv})', ({
                    'session_handle_token': GLib.Variant('s', token),
                    'handle_token': GLib.Variant('s', token),
                },)),
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            
            # Run main loop (handles portal dialogs)
            print("🔄 Portal dialog bekleniyor...")
            self.loop.run()
            
        except Exception as e:
            print(f"❌ Portal hatası: {e}")
            self.cleanup()
            return False
            
        return True
        
    def _on_response(self, connection, sender, path, interface, signal_name, params, user_data):
        """Handle portal response signals."""
        response, results = params.unpack()
        
        if response != 0:
            print(f"❌ Kullanıcı iptal etti veya hata: {response}")
            self.cleanup()
            self.loop.quit()
            return
            
        if 'session_handle' in results:
            # Session created, now select sources
            self.session_handle = results['session_handle']
            print(f"✅ Session: {self.session_handle}")
            
            # Select sources (show screen picker)
            token = f"select_{os.getpid()}"
            self.portal.call_sync(
                'SelectSources',
                GLib.Variant('(oa{sv})', (
                    self.session_handle,
                    {
                        'types': GLib.Variant('u', 1),  # MONITOR only
                        'multiple': GLib.Variant('b', False),
                        'handle_token': GLib.Variant('s', token),
                    }
                )),
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            
        elif 'streams' not in results and self.session_handle:
            # Sources selected, now start
            token = f"start_{os.getpid()}"
            self.portal.call_sync(
                'Start',
                GLib.Variant('(osa{sv})', (
                    self.session_handle,
                    '',  # parent window
                    {
                        'handle_token': GLib.Variant('s', token),
                    }
                )),
                Gio.DBusCallFlags.NONE,
                -1,
                None
            )
            
        elif 'streams' in results:
            # Got the stream!
            streams = results['streams']
            if streams:
                self.node_id = streams[0][0]
                with open(NODE_FILE, 'w') as f:
                    f.write(str(self.node_id))
                print(f"✅ Stream hazır: node={self.node_id}")
                # Don't quit - keep running to maintain session
            else:
                print("❌ Stream alınamadı")
                self.cleanup()
                self.loop.quit()
    
    def cleanup(self):
        """Clean up session files."""
        for f in [NODE_FILE, PID_FILE]:
            try:
                os.unlink(f)
            except:
                pass
                
    def stop(self):
        """Stop running service."""
        if os.path.exists(PID_FILE):
            try:
                with open(PID_FILE, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, signal.SIGTERM)
                print(f"✅ Service stopped (PID {pid})")
            except ProcessLookupError:
                print("⚠️ Service not running")
            except Exception as e:
                print(f"⚠️ {e}")
        self.cleanup()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        service = PortalScreenCast()
        if cmd == 'start':
            service.start()
        elif cmd == 'stop':
            service.stop()
    else:
        print("Usage: portal_service.py [start|stop]")
