"""
Tool Executor - Execute AtomBase tools
"""
import os
import sys

# Ensure project root is in path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core import state
from core.colors import Colors

# AtomBase tool imports
ATOMBASE_AVAILABLE = False
CODING_AVAILABLE = False
MEMORY_AVAILABLE = False
WEATHER_AVAILABLE = False
CAMERA_AVAILABLE = False
VISUAL_MEMORY_AVAILABLE = False
CAMERA_ENABLED = False

# Add AtomBase to path for its internal imports
_atombase_path = os.path.join(_project_root, "AtomBase")
if _atombase_path not in sys.path:
    sys.path.insert(0, _atombase_path)

try:
    from AtomBase.tools.basic import get_current_time, run_neofetch
    from AtomBase.tools.location import get_current_location
    from AtomBase.tools.files import list_files, read_file, write_file, scan_workspace
    from AtomBase.tools.execution import run_terminal_command
    from AtomBase.tools.coding import delegate_coding, save_generated_code
    from AtomBase.tools.memory import (
        save_context, get_context_info, get_memory_stats, clear_memory,
        add_to_history, get_all_context, get_user_name
    )
    from AtomBase.tools.weather import get_weather
    from AtomBase.tools.camera import capture_frame, get_camera_payload
    from AtomBase.tools.visual_memory import (
        save_visual_observation, get_visual_history, 
        compare_with_last, get_visual_context_for_prompt
    )
    ATOMBASE_AVAILABLE = True
    CODING_AVAILABLE = True
    MEMORY_AVAILABLE = True
    WEATHER_AVAILABLE = True
    CAMERA_AVAILABLE = True
    VISUAL_MEMORY_AVAILABLE = True
    CAMERA_ENABLED = CAMERA_AVAILABLE
except ImportError as e:
    print(f"{Colors.YELLOW}AtomBase araçları yüklenemedi: {e}{Colors.RESET}")


def execute_tool(name: str, args: dict) -> str:
    """Execute an AtomBase tool and return the result."""
    try:
        if name == "get_current_time":
            return get_current_time.invoke({})
        elif name == "get_current_location":
            import json
            # Use cached location if available (fetched at startup)
            if state.cached_location:
                return json.dumps(state.cached_location, ensure_ascii=False)
            result = get_current_location.invoke({})
            return json.dumps(result, ensure_ascii=False)
        elif name == "list_files":
            return list_files.invoke({"directory": args.get("directory", ".")})
        elif name == "read_file":
            return read_file.invoke({"filename": args["filename"]})
        elif name == "write_file":
            return write_file.invoke({"filename": args["filename"], "content": args["content"]})
        elif name == "scan_workspace":
            return scan_workspace.invoke({"max_depth": args.get("max_depth", 2)})
        elif name == "run_terminal_command":
            return run_terminal_command.invoke({"command": args["command"]})
        elif name == "run_neofetch":
            return run_neofetch.invoke({})
        elif name == "delegate_coding":
            if CODING_AVAILABLE:
                result = delegate_coding(args["prompt"], args.get("context", ""))
                if result["success"]:
                    workspace = os.path.join(os.path.dirname(os.path.dirname(__file__)), "atom_workspace")
                    os.makedirs(workspace, exist_ok=True)
                    filepath = save_generated_code(result["filename"], result["code"], workspace)
                    return f"✅ Kod oluşturuldu: {result['filename']}\n\n{result['explanation']}\n\nDosya: {filepath}"
                else:
                    return f"❌ Kod oluşturulamadı: {result.get('error', 'Bilinmeyen hata')}"
            return "Coding module not available"
        # Memory tools
        elif name == "save_context":
            if MEMORY_AVAILABLE:
                return save_context(args["key"], args["value"])
            return "Memory module not available"
        elif name == "get_context_info":
            if MEMORY_AVAILABLE:
                return get_context_info(args["key"])
            return "Memory module not available"
        elif name == "get_memory_stats":
            if MEMORY_AVAILABLE:
                return get_memory_stats()
            return "Memory module not available"
        elif name == "clear_memory":
            if MEMORY_AVAILABLE:
                return clear_memory()
            return "Memory module not available"
        # Weather tool
        elif name == "get_weather":
            if WEATHER_AVAILABLE:
                return get_weather(args["city"])
            return "Weather module not available"
        # Camera tool removed - frames are sent automatically via VAD in audio/video.py
        # Exit tool
        elif name == "exit_app":
            state.exit_requested = True
            return "Güle güle! Seninle sohbet etmek güzeldi. Tekrar görüşmek üzere!"
        # Visual Memory Tools
        elif name == "save_visual_observation":
            if VISUAL_MEMORY_AVAILABLE:
                return save_visual_observation(args["notes"])
            return "Görsel hafıza kullanılamıyor"
        elif name == "get_visual_history":
            if VISUAL_MEMORY_AVAILABLE:
                return get_visual_history()
            return "Görsel hafıza kullanılamıyor"
        # Screen Sharing Tools
        elif name == "share_screen":
            state.video_mode = "screen"
            return "🖥️ Tamam! Kamerayı kapatıp ekranını izlemeye başlıyorum. 'Ekranı bırakabilirsin' dediğinde geri kameraya döneceğim."
        elif name == "stop_screen_share":
            state.video_mode = "camera"
            return "📷 Ekran paylaşımı durduruldu. Kameraya geri dönüyorum!"
        # Proactive Tools
        elif name == "set_reminder":
            from core.proactive import set_reminder as _set_reminder
            return _set_reminder(args["duration_seconds"], args["message"])
        elif name == "set_watcher":
            from core.proactive import set_watcher as _set_watcher
            return _set_watcher(args["condition"], args["message"])
            
        elif name == "learn_proactive_rule":
            from core.learning import add_vision_rule
            return add_vision_rule(args.get("rule"))
            
        elif name == "computer_control":
            from core.computer import mouse_move, mouse_click, keyboard_type, keyboard_key
            action = args.get("action")
            if action == "move":
                return mouse_move(args.get("x"), args.get("y"))
            elif action == "click":
                return mouse_click(x=args.get("x"), y=args.get("y"))
            elif action == "type":
                return keyboard_type(args.get("text"))
            elif action == "key":
                return keyboard_key(args.get("text"))
            return "Unknown action"
            
        elif name == "find_ui_element":
            from core.vision_analyzer import find_element_on_screen
            from core.state import latest_image_payload
            from core.computer import get_screen_size
            import asyncio
            import threading
            
            # Use active state to get image
            if not latest_image_payload:
                return "Error: No screen image available."
            
            # Run async function in a new loop in a new thread to be safe
            result_container = {}
            
            def run_in_thread(element, image, container):
                try:
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    res = new_loop.run_until_complete(find_element_on_screen(element, image))
                    container['result'] = res
                    new_loop.close()
                except Exception as e:
                    container['error'] = str(e)

            # Start thread and join (blocking this tool execution, but that's what we want for sync return)
            t = threading.Thread(target=run_in_thread, args=(args.get("element_name"), latest_image_payload, result_container))
            t.start()
            t.join(timeout=10) # 10s timeout
            
            if t.is_alive():
                 return "Error: Timeout looking for element."
                 
            result = result_container.get("result", {})
            error = result_container.get("error")
            
            if error:
                return f"Error finding element: {error}"
            
            if result.get("found"):
                # Convert 0-1000 to pixels
                # Assume 1920x1080 for now if get_screen_size fails
                WIDTH, HEIGHT = 1920, 1080
                try:
                    # Parse "1920x1080" from get_screen_size
                    dims = get_screen_size().strip().split("x")
                    if len(dims) == 2:
                        WIDTH, HEIGHT = int(dims[0]), int(dims[1])
                except:
                    pass
                    
                # Gemini returns [ymin, xmin, ymax, xmax] 0-1000
                coords = result.get("coordinates") #[ymin, xmin, ymax, xmax]
                if coords:
                    ymin, xmin, ymax, xmax = coords
                    center_x_norm = (xmin + xmax) / 2
                    center_y_norm = (ymin + ymax) / 2
                else:
                    center_x_norm = result.get("center_x", 500)
                    center_y_norm = result.get("center_y", 500)
                
                pixel_x = int((center_x_norm / 1000) * WIDTH)
                pixel_y = int((center_y_norm / 1000) * HEIGHT)
                
                return f"Found '{args.get('element_name')}' at [{pixel_x}, {pixel_y}]. Use computer_control(action='click', x={pixel_x}, y={pixel_y}) to click."
            else:
                return f"Could not find '{args.get('element_name')}' on screen."
            
        else:
            return f"Unknown tool: {name}"
    except Exception as e:
        return f"Tool error: {str(e)}"
