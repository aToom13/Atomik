"""
Global State Variables
"""

# Camera frame state
pending_camera_frame = None
exit_requested = False

# Video Mode (camera, screen, or workspace)
video_mode = "camera"  # "camera" or "screen" or "workspace" (sanal ekran :99)

# VAD State
latest_image_payload = None
is_speaking = False
last_frame_time = 0

# Active Loop Reference
active_loop = None

# Cached Location (fetched at startup)
cached_location = None

# Echo Cancellation - Atomik konuşurken mikrofon eşiğini yükselt
atomik_is_speaking = False
