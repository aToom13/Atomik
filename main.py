"""
Atomik - Realtime Voice Chat with AtomBase Tool Calling
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from audio import AudioLoop, cleanup
from core.colors import Colors


async def main():
    audio_loop = AudioLoop()
    await audio_loop.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.CYAN}Hoşça kal!{Colors.RESET}")
    finally:
        cleanup()
