"""
Atomik - Realtime Voice Chat with AtomBase Tool Calling
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio import AudioLoop, cleanup
from audio.local_loop import LocalAudioLoop
from core.colors import Colors
import argparse


async def main():
    parser = argparse.ArgumentParser(description='Atomik Voice Assistant')
    parser.add_argument('--off', '--offline', action='store_true', dest='offline', help='Force offline mode')
    parser.add_argument('--avatar', action='store_true', help='Launch with Live2D avatar window')
    args = parser.parse_args()

    # Avatar mode - GTK window with Live2D
    if args.avatar:
        print(f"{Colors.MAGENTA}🎭 Avatar Modu başlatılıyor...{Colors.RESET}")
        from ui.gtk_app import run_avatar_mode
        run_avatar_mode(offline=args.offline)
        return

    if args.offline:
        print(f"{Colors.YELLOW}🛠️ Offline Mod zorlandı (--offline){Colors.RESET}")
        loop = LocalAudioLoop()
    else:
        loop = AudioLoop()
        
    await loop.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.CYAN}Hoşça kal!{Colors.RESET}")
    finally:
        cleanup()
