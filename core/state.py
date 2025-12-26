"""
Global State Variables
"""

# Camera frame state
pending_camera_frame = None
exit_requested = False

# Video Mode (camera or screen)
video_mode = "camera"  # "camera" or "screen"

# VAD State
latest_image_payload = None
is_speaking = False
last_frame_time = 0

# Active Loop Reference
active_loop = None
