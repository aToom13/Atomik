"""
ANSI Colors for TUI
"""

class Colors:
    RESET = "\033[0m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RED = "\033[91m"


def print_header():
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("╔══════════════════════════════════════════════════╗")
    print("║      ATOMIK + AtomBase - Voice Assistant         ║")
    print("╚══════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}")
    print("Press Ctrl+C to exit\n")
