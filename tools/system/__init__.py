"""
Atomik System Tools
"""
# Camera tools
from .camera import capture_frame, get_camera_payload

# Location tools
from .location import get_current_location

# Weather tools
from .weather import get_weather

# Workspace tools
from .workspace import (
    start_virtual_workspace,
    stop_virtual_workspace,
    capture_active_window,
    release_captured_window,
    open_app_in_workspace,
    type_in_workspace,
    send_key_in_workspace,
    click_in_workspace
)
