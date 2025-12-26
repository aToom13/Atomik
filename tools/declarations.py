"""
Tool Declarations for Gemini Live API
"""

from core.learning import add_vision_rule
from core.computer import mouse_move, mouse_click, keyboard_type, keyboard_key
from core.state import active_loop  # Access to active loop for latest image

TOOL_DECLARATIONS = [
    {
        "name": "get_current_time",
        "description": "Returns the current local time formatted as YYYY-MM-DD HH:MM:SS.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "list_files",
        "description": "Lists files in a directory within the workspace.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "directory": {
                    "type": "STRING",
                    "description": "Directory path relative to workspace (default: '.')"
                }
            }
        }
    },
    {
        "name": "read_file",
        "description": "Reads content from a file in the workspace.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "filename": {
                    "type": "STRING",
                    "description": "Path to the file to read"
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "write_file",
        "description": "Writes content to a file in the workspace. Overwrites if exists.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "filename": {
                    "type": "STRING",
                    "description": "Path to the file to write"
                },
                "content": {
                    "type": "STRING",
                    "description": "Content to write to the file"
                }
            },
            "required": ["filename", "content"]
        }
    },
    {
        "name": "scan_workspace",
        "description": "Scans the workspace and returns a file tree structure.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "max_depth": {
                    "type": "INTEGER",
                    "description": "Maximum directory depth (default: 2)"
                }
            }
        }
    },
    {
        "name": "run_terminal_command",
        "description": "Executes a terminal command in the workspace.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "The command to execute"
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "run_neofetch",
        "description": "Displays system information with ASCII art using neofetch.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "delegate_coding",
        "description": "Kod yazma isteğini daha akıllı bir modele (Gemini 3 Flash) ilet.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt": {"type": "STRING", "description": "Kullanıcının kod isteği."},
                "context": {"type": "STRING", "description": "Opsiyonel bağlam bilgisi"}
            },
            "required": ["prompt"]
        },
        "behavior": "NON_BLOCKING"
    },
    # Memory Tools
    {
        "name": "save_context",
        "description": "Önemli bilgiyi hafızaya kaydet.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {"type": "STRING", "description": "Bilgi anahtarı"},
                "value": {"type": "STRING", "description": "Kaydedilecek değer"}
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "get_context_info",
        "description": "Hafızadan bilgi getir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {"type": "STRING", "description": "Bilgi anahtarı"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "get_memory_stats",
        "description": "Hafızadaki tüm bilgilerin özetini göster.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "clear_memory",
        "description": "Hafızayı temizle.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    # Weather Tool
    {
        "name": "get_weather",
        "description": "Şehir için hava durumu sorgula.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "Şehir adı"}
            },
            "required": ["city"]
        }
    },
    # Exit Tool (capture_frame removed - camera is always active via VAD)
    {
        "name": "exit_app",
        "description": "Uygulamadan çık. Hoşçakal, görüşürüz gibi şeyler söylendiğinde.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    # Visual Memory Tools
    {
        "name": "save_visual_observation",
        "description": "Kullanıcının görünümünü kaydet (gözlük, saç, kıyafet vb.).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "notes": {"type": "STRING", "description": "Görsel gözlem notları"}
            },
            "required": ["notes"]
        }
    },
    {
        "name": "get_visual_history",
        "description": "Önceki görsel gözlemleri getir.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    # Screen Sharing Tools
    {
        "name": "share_screen",
        "description": "Kullanıcının ekranını görmeye başla.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "stop_screen_share",
        "description": "Ekran paylaşımını durdur ve kameraya geri dön.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    # Proactive Tools
    {
        "name": "set_reminder",
        "description": "Hatırlatıcı kur. Örn: '5 dakika sonra hatırlat' veya '30 saniye sonra söyle'.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "duration_seconds": {"type": "INTEGER", "description": "Kaç saniye sonra hatırlatılsın"},
                "message": {"type": "STRING", "description": "Hatırlatılacak mesaj"}
            },
            "required": ["duration_seconds", "message"]
        }
    },
    {
        "name": "set_watcher",
        "description": "Ekran/kamera izleyici kur. Belirtilen durum olunca haber ver.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "condition": {"type": "STRING", "description": "İzlenecek durum (örn: 'ekranda hata mesajı görünürse')"},
                "message": {"type": "STRING", "description": "Durum gerçekleşince söylenecek mesaj"}
            },
            "required": ["condition", "message"]
        }
    },
    {
        "name": "learn_proactive_rule",
        "description": "Adds a new rule for when the assistant should speak or stay silent based on user feedback. Use this when the user corrects your behavior (e.g., 'Don't interrupt me when I'm reading').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "rule": {
                    "type": "STRING",
                    "description": "The rule to learn (e.g., 'Do not comment on phone usage', 'Always greet when I wave')."
                }
            },
            "required": ["rule"]
        }
    },
    {
        "name": "computer_control",
        "description": "Control computer mouse and keyboard. Use this when the user asks to click, type, or press keys on the screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "enum": ["move", "click", "type", "key"], "description": "Action to perform"},
                "x": {"type": "INTEGER", "description": "X coordinate for move"},
                "y": {"type": "INTEGER", "description": "Y coordinate for move"},
                "text": {"type": "STRING", "description": "Text to type or key to press (for 'key' action)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "find_ui_element",
        "description": "Finds coordinates of a UI element on the screen by name. Use this BEFORE clicking to know where to click.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "element_name": {"type": "STRING", "description": "Name of the element (e.g., 'Spotify icon', 'Send button', 'Search bar')"}
            },
            "required": ["element_name"]
        }
    }
]
