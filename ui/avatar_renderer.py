"""
Live2D Renderer for GTK4/OpenGL
Arch modeli için moc3 render wrapper
"""
import os
import math
import random
from typing import Optional, Dict, Any

# Live2D import - fallback if not installed
try:
    import live2d.v3 as live2d
    from live2d.v3 import LAppModel
    LIVE2D_AVAILABLE = True
except ImportError:
    LIVE2D_AVAILABLE = False
    print("[Avatar] ⚠️ live2d-py not installed. Run: pip install live2d-py")

# OpenGL imports
try:
    from OpenGL import GL
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False
    print("[Avatar] ⚠️ PyOpenGL not installed. Run: pip install PyOpenGL")


class Live2DRenderer:
    """
    Live2D model renderer for GTK GLArea integration.
    Handles model loading, parameter updates, and OpenGL rendering.
    """
    
    # Standard Live2D parameter names
    PARAM_MOUTH_OPEN_Y = "ParamMouthOpenY"
    PARAM_EYE_L_OPEN = "ParamEyeLOpen"
    PARAM_EYE_R_OPEN = "ParamEyeROpen"
    PARAM_EYE_BALL_X = "ParamEyeBallX"
    PARAM_EYE_BALL_Y = "ParamEyeBallY"
    PARAM_ANGLE_X = "ParamAngleX"
    PARAM_ANGLE_Y = "ParamAngleY"
    PARAM_ANGLE_Z = "ParamAngleZ"
    PARAM_BODY_ANGLE_X = "ParamBodyAngleX"
    PARAM_BODY_ANGLE_Y = "ParamBodyAngleY"
    PARAM_ARM_L = "ParamArmLA"  # Left arm
    PARAM_ARM_R = "ParamArmRA"  # Right arm
    
    def __init__(self):
        self.model: Optional[Any] = None
        self.model_path: Optional[str] = None
        self.width = 800
        self.height = 600
        self.initialized = False
        
        # Current parameter values (for smooth interpolation)
        self._params: Dict[str, float] = {}
        self._target_params: Dict[str, float] = {}
        
    def initialize(self, width: int, height: int) -> bool:
        """Initialize Live2D framework. Call after OpenGL context is ready."""
        if not LIVE2D_AVAILABLE:
            print("[Avatar] Cannot initialize - live2d-py not available")
            return False
            
        self.width = width
        self.height = height
        
        try:
            live2d.init()
            live2d.glewInit()
            self.initialized = True
            print(f"[Avatar] ✅ Live2D initialized ({width}x{height})")
            return True
        except Exception as e:
            print(f"[Avatar] ❌ Live2D init failed: {e}")
            return False
    
    def load_model(self, model_json_path: str) -> bool:
        """
        Load a Live2D model from .model3.json file.
        Example: load_model("/path/to/Arch/arch chan model0.model3.json")
        """
        if not self.initialized:
            print("[Avatar] Must call initialize() first")
            return False
            
        if not os.path.exists(model_json_path):
            print(f"[Avatar] Model not found: {model_json_path}")
            return False
        
        try:
            self.model = LAppModel()
            self.model.LoadModelJson(model_json_path)
            self.model.Resize(self.width, self.height)
            self.model_path = model_json_path
            
            # Initialize default parameters
            self._init_default_params()
            
            print(f"[Avatar] ✅ Model loaded: {os.path.basename(model_json_path)}")
            return True
        except Exception as e:
            print(f"[Avatar] ❌ Model load failed: {e}")
            self.model = None
            return False
    
    def _init_default_params(self):
        """Set default parameter values"""
        defaults = {
            self.PARAM_EYE_L_OPEN: 1.0,
            self.PARAM_EYE_R_OPEN: 1.0,
            self.PARAM_MOUTH_OPEN_Y: 0.0,
            self.PARAM_ANGLE_X: 0.0,
            self.PARAM_ANGLE_Y: 0.0,
            self.PARAM_ANGLE_Z: 0.0,
            self.PARAM_EYE_BALL_X: 0.0,
            self.PARAM_EYE_BALL_Y: 0.0,
        }
        self._params = defaults.copy()
        self._target_params = defaults.copy()
    
    def resize(self, width: int, height: int):
        """Update viewport size"""
        self.width = width
        self.height = height
        if self.model:
            self.model.Resize(width, height)
    
    # ==================== Parameter Setters ====================
    
    def set_mouth_open(self, value: float):
        """Set mouth openness (0.0 = closed, 1.0 = fully open)"""
        self._target_params[self.PARAM_MOUTH_OPEN_Y] = max(0.0, min(1.0, value))
    
    def set_eye_open(self, left: float, right: float):
        """Set eye openness (0.0 = closed, 1.0 = open)"""
        self._target_params[self.PARAM_EYE_L_OPEN] = max(0.0, min(1.0, left))
        self._target_params[self.PARAM_EYE_R_OPEN] = max(0.0, min(1.0, right))
    
    def set_eye_ball(self, x: float, y: float):
        """Set eye ball position (-1.0 to 1.0)"""
        self._target_params[self.PARAM_EYE_BALL_X] = max(-1.0, min(1.0, x))
        self._target_params[self.PARAM_EYE_BALL_Y] = max(-1.0, min(1.0, y))
    
    def set_head_angle(self, x: float, y: float, z: float):
        """Set head rotation angles"""
        self._target_params[self.PARAM_ANGLE_X] = x
        self._target_params[self.PARAM_ANGLE_Y] = y
        self._target_params[self.PARAM_ANGLE_Z] = z
    
    def set_body_angle(self, x: float, y: float = 0.0):
        """Set body rotation"""
        self._target_params[self.PARAM_BODY_ANGLE_X] = x
        self._target_params[self.PARAM_BODY_ANGLE_Y] = y
    
    def set_arm(self, left: float = 0.0, right: float = 0.0):
        """Set arm positions for waving gesture"""
        self._target_params[self.PARAM_ARM_L] = left
        self._target_params[self.PARAM_ARM_R] = right
    
    def set_parameter(self, name: str, value: float):
        """Generic parameter setter"""
        self._target_params[name] = value
    
    # ==================== Update & Render ====================
    
    def update(self, delta_time: float):
        """
        Update model state and interpolate parameters.
        Call this every frame before draw().
        """
        if not self.model:
            return
        
        # Smooth interpolation of parameters
        lerp_speed = 10.0 * delta_time
        for param, target in self._target_params.items():
            current = self._params.get(param, 0.0)
            self._params[param] = current + (target - current) * min(lerp_speed, 1.0)
        
        # Apply parameters to model
        for param, value in self._params.items():
            try:
                self.model.SetParameterValue(param, value)
            except:
                pass  # Parameter might not exist in this model
        
        # Update model physics and animations
        self.model.Update(delta_time)
    
    def draw(self):
        """
        Render the model to current OpenGL context.
        Call this in GLArea's render callback.
        """
        if not self.model:
            return
        
        # Clear with transparent background
        GL.glClearColor(0.0, 0.0, 0.0, 0.0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        
        # Draw model
        self.model.Draw()
    
    def cleanup(self):
        """Release resources"""
        if self.model:
            del self.model
            self.model = None
        if LIVE2D_AVAILABLE and self.initialized:
            live2d.dispose()
            self.initialized = False
