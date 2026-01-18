"""
Avatar Controller - Animation State Machine
Manages lip sync, blinking, idle motions, and AI-triggered gestures
"""
import time
import random
import math
from typing import Optional, Callable, Dict, Any
from enum import Enum, auto

from .avatar_renderer import Live2DRenderer


class GestureType(Enum):
    """Available gesture types that AI can trigger"""
    WAVE = auto()         # El sallama
    NOD = auto()          # Baş sallama (onay)
    SHAKE_HEAD = auto()   # Baş sallama (hayır)
    SMILE = auto()        # Gülümseme
    THINK = auto()        # Düşünme
    EXCITED = auto()      # Heyecanlanma
    SAD = auto()          # Üzgün
    SURPRISED = auto()    # Şaşırma


class AvatarController:
    """
    Controls avatar animations based on audio output and AI gestures.
    Acts as Atomik's "body" - the bridge between AI intent and visual expression.
    """
    
    def __init__(self, renderer: Live2DRenderer):
        self.renderer = renderer
        
        # Timing
        self._last_update = time.time()
        self._time_elapsed = 0.0
        
        # Blink state
        self._blink_timer = 0.0
        self._next_blink = random.uniform(2.5, 5.0)
        self._blink_progress = 0.0  # 0 = open, 1 = closed
        self._is_blinking = False
        
        # Idle motion state
        self._idle_phase = random.uniform(0, 2 * math.pi)
        
        # Lip sync state
        self._current_mouth_open = 0.0
        self._target_mouth_open = 0.0
        
        # Gesture state
        self._current_gesture: Optional[Dict[str, Any]] = None
        self._gesture_progress = 0.0
        
        # Expression state
        self._current_expression = "idle"
        
    # ==================== Main Update Loop ====================
    
    def update(self):
        """
        Main update loop - call this every frame.
        Updates all animation states.
        """
        now = time.time()
        delta_time = now - self._last_update
        self._last_update = now
        self._time_elapsed += delta_time
        
        # Update all animation systems
        self._update_blink(delta_time)
        self._update_idle(delta_time)
        self._update_lip_sync(delta_time)
        self._update_gesture(delta_time)
        
        # Apply to renderer
        self.renderer.update(delta_time)
    
    # ==================== Blink System ====================
    
    def _update_blink(self, delta_time: float):
        """Auto-blink with random intervals"""
        if self._is_blinking:
            # Blink animation (close then open)
            self._blink_progress += delta_time * 8.0  # Fast blink
            
            if self._blink_progress < 0.5:
                # Closing
                eye_value = 1.0 - (self._blink_progress * 2.0)
            elif self._blink_progress < 1.0:
                # Opening
                eye_value = (self._blink_progress - 0.5) * 2.0
            else:
                # Blink complete
                self._is_blinking = False
                self._blink_progress = 0.0
                self._next_blink = random.uniform(2.5, 5.0)
                eye_value = 1.0
            
            self.renderer.set_eye_open(eye_value, eye_value)
        else:
            self._blink_timer += delta_time
            if self._blink_timer >= self._next_blink:
                self._is_blinking = True
                self._blink_timer = 0.0
    
    # ==================== Idle Motion ====================
    
    def _update_idle(self, delta_time: float):
        """Subtle idle breathing/swaying motion"""
        # Slow breathing motion
        breath_cycle = math.sin(self._time_elapsed * 0.8) * 0.3
        
        # Subtle head sway
        head_x = math.sin(self._time_elapsed * 0.3 + self._idle_phase) * 2.0
        head_y = math.sin(self._time_elapsed * 0.4) * 1.5
        head_z = math.sin(self._time_elapsed * 0.2) * 1.0
        
        # Apply only if no gesture is active
        if not self._current_gesture:
            self.renderer.set_head_angle(head_x, head_y, head_z)
            self.renderer.set_body_angle(breath_cycle)
    
    # ==================== Lip Sync ====================
    
    def _update_lip_sync(self, delta_time: float):
        """Smooth lip sync interpolation"""
        # Lerp towards target
        lerp_speed = 15.0 * delta_time
        self._current_mouth_open += (self._target_mouth_open - self._current_mouth_open) * min(lerp_speed, 1.0)
        self.renderer.set_mouth_open(self._current_mouth_open)
    
    def on_audio_level(self, level: float):
        """
        Callback from AudioLoop - receives audio output level (0.0-1.0).
        Maps to mouth openness for lip sync.
        """
        # Apply some smoothing and mapping
        # Higher levels = more open mouth
        self._target_mouth_open = min(level * 1.2, 1.0)  # Slight boost
    
    # ==================== Gesture System ====================
    
    def trigger_gesture(self, gesture: str, intensity: float = 0.7):
        """
        Trigger a gesture animation. Called by AI via express_gesture tool.
        
        Args:
            gesture: One of wave, nod, shake_head, smile, think, excited, sad, surprised
            intensity: 0.0 to 1.0, how pronounced the gesture should be
        """
        try:
            gesture_type = GestureType[gesture.upper()]
        except KeyError:
            print(f"[Avatar] Unknown gesture: {gesture}")
            return
        
        self._current_gesture = {
            "type": gesture_type,
            "intensity": max(0.0, min(1.0, intensity)),
            "progress": 0.0,
            "duration": self._get_gesture_duration(gesture_type)
        }
        self._gesture_progress = 0.0
        print(f"[Avatar] 🎭 Gesture triggered: {gesture} (intensity: {intensity})")
    
    def _get_gesture_duration(self, gesture_type: GestureType) -> float:
        """Get duration for each gesture type"""
        durations = {
            GestureType.WAVE: 1.5,
            GestureType.NOD: 0.8,
            GestureType.SHAKE_HEAD: 1.0,
            GestureType.SMILE: 2.0,
            GestureType.THINK: 2.5,
            GestureType.EXCITED: 1.2,
            GestureType.SAD: 2.0,
            GestureType.SURPRISED: 0.6,
        }
        return durations.get(gesture_type, 1.0)
    
    def _update_gesture(self, delta_time: float):
        """Update active gesture animation"""
        if not self._current_gesture:
            return
        
        gesture = self._current_gesture
        duration = gesture["duration"]
        intensity = gesture["intensity"]
        
        # Update progress
        gesture["progress"] += delta_time / duration
        progress = gesture["progress"]
        
        if progress >= 1.0:
            # Gesture complete - reset
            self._current_gesture = None
            return
        
        # Apply gesture-specific animation
        gesture_type = gesture["type"]
        
        if gesture_type == GestureType.WAVE:
            self._animate_wave(progress, intensity)
        elif gesture_type == GestureType.NOD:
            self._animate_nod(progress, intensity)
        elif gesture_type == GestureType.SHAKE_HEAD:
            self._animate_shake_head(progress, intensity)
        elif gesture_type == GestureType.SMILE:
            self._animate_smile(progress, intensity)
        elif gesture_type == GestureType.THINK:
            self._animate_think(progress, intensity)
        elif gesture_type == GestureType.EXCITED:
            self._animate_excited(progress, intensity)
        elif gesture_type == GestureType.SAD:
            self._animate_sad(progress, intensity)
        elif gesture_type == GestureType.SURPRISED:
            self._animate_surprised(progress, intensity)
    
    # ==================== Gesture Animations ====================
    
    def _animate_wave(self, progress: float, intensity: float):
        """Wave hand animation - selamlaşma"""
        # Sine wave for arm movement
        wave_angle = math.sin(progress * math.pi * 4) * 30 * intensity
        
        # Raise arm during wave
        arm_raise = math.sin(progress * math.pi) * intensity
        
        self.renderer.set_arm(right=arm_raise)
        self.renderer.set_head_angle(
            math.sin(progress * math.pi * 2) * 5 * intensity,  # Slight head bob
            0, 
            wave_angle * 0.1
        )
    
    def _animate_nod(self, progress: float, intensity: float):
        """Nod head - onay"""
        # Up-down motion
        nod_angle = math.sin(progress * math.pi * 2) * 15 * intensity
        self.renderer.set_head_angle(0, nod_angle, 0)
    
    def _animate_shake_head(self, progress: float, intensity: float):
        """Shake head - hayır"""
        # Left-right motion
        shake_angle = math.sin(progress * math.pi * 4) * 20 * intensity
        self.renderer.set_head_angle(shake_angle, 0, 0)
    
    def _animate_smile(self, progress: float, intensity: float):
        """Smile expression"""
        # Fade in/out smile
        smile_amount = math.sin(progress * math.pi) * intensity
        self.renderer.set_parameter("ParamMouthForm", smile_amount)
        
        # Slight eye squint when smiling
        eye_squint = 1.0 - (smile_amount * 0.2)
        self.renderer.set_eye_open(eye_squint, eye_squint)
    
    def _animate_think(self, progress: float, intensity: float):
        """Thinking pose - look up/side"""
        # Look up and to side
        think_progress = math.sin(progress * math.pi)
        self.renderer.set_eye_ball(0.5 * intensity * think_progress, 0.3 * intensity * think_progress)
        self.renderer.set_head_angle(
            5 * intensity * think_progress,
            -8 * intensity * think_progress,
            -5 * intensity * think_progress
        )
    
    def _animate_excited(self, progress: float, intensity: float):
        """Excited bounce"""
        # Quick bounce motion
        bounce = abs(math.sin(progress * math.pi * 6)) * intensity
        self.renderer.set_body_angle(bounce * 5)
        self.renderer.set_parameter("ParamMouthForm", 0.8 * intensity)  # Big smile
    
    def _animate_sad(self, progress: float, intensity: float):
        """Sad drooping"""
        sad_amount = math.sin(progress * math.pi) * intensity
        self.renderer.set_head_angle(0, 10 * sad_amount, 0)  # Head down
        self.renderer.set_eye_ball(0, -0.3 * sad_amount)  # Look down
        self.renderer.set_parameter("ParamBrowLY", -sad_amount * 0.5)
        self.renderer.set_parameter("ParamBrowRY", -sad_amount * 0.5)
    
    def _animate_surprised(self, progress: float, intensity: float):
        """Surprised reaction"""
        surprise_amount = math.sin(progress * math.pi) * intensity
        # Wide eyes
        self.renderer.set_eye_open(1.0 + surprise_amount * 0.3, 1.0 + surprise_amount * 0.3)
        # Raised eyebrows
        self.renderer.set_parameter("ParamBrowLY", surprise_amount * 0.5)
        self.renderer.set_parameter("ParamBrowRY", surprise_amount * 0.5)
        # Open mouth slightly
        self.renderer.set_mouth_open(surprise_amount * 0.4)
    
    # ==================== Expression Control ====================
    
    def set_expression(self, expression: str):
        """
        Set a persistent expression (idle, smirk, blink).
        These are defined in model3.json Expressions.
        """
        # Would call model.SetExpression() if using motion files
        self._current_expression = expression
        print(f"[Avatar] Expression set: {expression}")
