"""
Camera Tool for Atomik
Captures frame from webcam for visual analysis
"""
import os
import base64
import io

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def capture_frame(camera_index: int = 0) -> dict:
    """
    Capture a frame from webcam and return as base64.
    
    Args:
        camera_index: Camera device index (default 0)
    
    Returns:
        dict with 'success', 'data' (base64), 'mime_type', 'error'
    """
    if not CV2_AVAILABLE:
        return {
            "success": False,
            "error": "opencv-python yüklü değil. pip install opencv-python",
            "data": None,
            "mime_type": None
        }
    
    if not PIL_AVAILABLE:
        return {
            "success": False,
            "error": "Pillow yüklü değil. pip install pillow",
            "data": None,
            "mime_type": None
        }
    
    try:
        # Open camera
        cap = cv2.VideoCapture(camera_index)
        
        if not cap.isOpened():
            return {
                "success": False,
                "error": f"Kamera {camera_index} açılamadı",
                "data": None,
                "mime_type": None
            }
        
        # Capture frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            return {
                "success": False,
                "error": "Frame alınamadı",
                "data": None,
                "mime_type": None
            }
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert to PIL Image
        img = Image.fromarray(frame_rgb)
        
        # Resize if too large (max 1024x1024)
        img.thumbnail([1024, 1024])
        
        # Convert to JPEG bytes
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)
        
        # Encode to base64
        image_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return {
            "success": True,
            "data": image_b64,
            "mime_type": "image/jpeg",
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": None,
            "mime_type": None
        }


def get_camera_payload(camera_index: int = 0) -> dict:
    """
    Get camera frame as payload for Gemini API.
    
    Returns:
        dict ready to send to out_queue, or None if failed
    """
    result = capture_frame(camera_index)
    
    if result["success"]:
        return {
            "data": base64.b64decode(result["data"]),
            "mime_type": result["mime_type"]
        }
    return None


# Test
if __name__ == "__main__":
    result = capture_frame()
    print("Success:", result["success"])
    if result["success"]:
        print("Data length:", len(result["data"]))
    else:
        print("Error:", result["error"])
