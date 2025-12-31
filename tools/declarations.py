"""
Tool Declarations for Gemini Live API
Performance: Cached at module load
"""

# ============================================================================
# PERFORMANCE: Declarations are cached at module import time
# ============================================================================
_DECLARATIONS_CACHE = None

def get_declarations():
    """Get cached tool declarations (faster than re-evaluating list)"""
    global _DECLARATIONS_CACHE
    if _DECLARATIONS_CACHE is None:
        _DECLARATIONS_CACHE = TOOL_DECLARATIONS
    return _DECLARATIONS_CACHE


TOOL_DECLARATIONS = [
    {
        "name": "get_current_time",
        "description": "Returns the current local time formatted as YYYY-MM-DD HH:MM:SS.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "get_current_location",
        "description": "Get current location info (city, country, lat, lon) based on IP address.",
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
    # ===== UNIFIED MEMORY TOOLS =====
    {
        "name": "manage_memory",
        "description": "Unified tool to save/update/delete all types of memory (context, long-term, mood, preferences, projects, learning rules). Use this for ANY 'remember', 'save', 'learn', or 'log' action.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "enum": ["save", "update", "delete"], "description": "Action type"},
                "category": {
                    "type": "STRING", 
                    "enum": ["context", "long_term", "mood", "preference", "project", "learning", "visual", "proactive_rule"],
                    "description": "Memory category"
                },
                "key": {"type": "STRING", "description": "Key/Topic/Mood/Filename depending on category"},
                "content": {"type": "STRING", "description": "Value/Summary/Notes/Rule depending on category"}
            },
            "required": ["action", "category"]
        }
    },
    {
        "name": "query_memory",
        "description": "Unified tool to retrieve ANY information from memory (short-term, long-term RAG, chat history, visual history, learned rules).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query or key"},
                "filter_type": {
                    "type": "STRING",
                    "enum": ["all", "context", "long_term", "chat", "learning", "visual"],
                    "description": "Filter per memory type (default: all)"
                },
                "time_range": {"type": "INTEGER", "description": "Look back N days (optional)"}
            },
            "required": ["query"]
        }
    },

    # ===== SCREEN SHARING TOOLS =====
    {
        "name": "share_screen",
        "description": "Starts sharing the user's screen. Use this when you need to see what's on the user's monitor continuously. Switches video source to screen.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "stop_screen_share",
        "description": "Stops sharing the user's screen and switches back to the camera.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "share_workspace_screen",
        "description": "Starts sharing the Virtual Workspace screen (DISPLAY=:99). Use this to see background apps.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    
    # ===== UNIFIED VISION TOOL =====
    {
        "name": "see_screen",
        "description": "Analyzes the current screen content using AI vision. Can read text, describe UI, or find elements.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task": {"type": "STRING", "enum": ["analyze", "read", "find"], "description": "Task type"},
                "region": {"type": "STRING", "description": "Region to analyze (e.g. 'sol', 'üst', 'merkez')"},
                "find": {"type": "STRING", "description": "Element/Text to find (only for 'find' task)"}
            },
            "required": ["task"]
        }
    },


    # ===== CODE QUALITY TOOLS =====
    {
        "name": "verify_code_quality",
        "description": "Runs linter (flake8), formatter (black), and tests (pytest) on a file. Replaces separate lint/format/test tools.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "filepath": {"type": "STRING", "description": "File to check"},
                "actions": {
                    "type": "ARRAY", 
                    "items": {"type": "STRING", "enum": ["lint", "format", "test"]},
                    "description": "Actions to perform (default: all)"
                }
            },
            "required": ["filepath"]
        }
    },

    # ===== VIRTUAL WORKSPACE TOOLS =====
    {
        "name": "start_virtual_workspace",
        "description": "Atomik'in bağımsız çalışma alanını başlatır. Kullanıcının ekranına dokunmadan arka planda çalışır.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "stop_virtual_workspace",
        "description": "Virtual workspace'i TAMAMEN KAPATIR. Sadece kullanıcı istediğinde çağır!",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "open_app_in_workspace",
        "description": "SANAL EKRAN'da uygulama açar. open_app_in_workspace sonrası virtual_input kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app": {"type": "STRING", "description": "Uygulama adı (spotify, firefox, gedit...)"},
                "maximize": {"type": "BOOLEAN", "description": "Tam ekran yap (varsayılan: true)"}
            },
            "required": ["app"]
        }
    },
    {
        "name": "virtual_input",
        "description": "Unified input tool for Virtual Workspace (click, type, key, focus). Use this to control apps in the virtual workspace.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "enum": ["click", "type", "key", "focus"], "description": "Action type"},
                "x": {"type": "INTEGER", "description": "X coordinate (for click)"},
                "y": {"type": "INTEGER", "description": "Y coordinate (for click)"},
                "text": {"type": "STRING", "description": "Text to type or key combo"},
                "window": {"type": "STRING", "description": "Window name (for focus)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "capture_active_window",
        "description": "Kullanıcının önündeki aktif pencereyi yakala ve 2. masaüstüne taşı.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "release_captured_window",
        "description": "Yakalanan pencereyi serbest bırak.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "view_captured_window",
        "description": "Yakalanan pencerenin anlık görüntüsünü al.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },

    # ===== WEATHER & SYSTEM =====
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
    # Exit Tool
    {
        "name": "exit_app",
        "description": "Uygulamadan çık.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    # Task Manager
    {
        "name": "add_task",
        "description": "Yeni görev ekle. Hatırlatıcı sistemi için.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Görev açıklaması"},
                "deadline": {"type": "STRING", "description": "Tarih (YYYY-MM-DD)"},
                "priority": {"type": "STRING", "description": "low/medium/high"},
                "category": {"type": "STRING", "description": "work/personal/shopping..."}
            },
            "required": ["action"]
        }
    },
    {
        "name": "complete_task",
        "description": "Görevi tamamla.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task_id": {"type": "STRING", "description": "Görev ID'si"}
            },
            "required": ["task_id"]
        }
    },
    {
        "name": "list_tasks",
        "description": "Görevleri listele.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "filter_type": {"type": "STRING", "description": "all/active/pending/completed/today"}
            }
        }
    },
    {
        "name": "get_task_summary",
        "description": "Günlük görev özeti al.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },

    # ===== COMPUTER CONTROL (REAL INPUT) =====
    {
        "name": "computer_control",
        "description": "Controls the REAL mouse and keyboard. Use this to click/type on the user's screen when sharing screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "enum": ["move", "click", "type", "key"], "description": "Action type"},
                "x": {"type": "INTEGER", "description": "X coordinate (for move/click)"},
                "y": {"type": "INTEGER", "description": "Y coordinate (for move/click)"},
                "text": {"type": "STRING", "description": "Text to type or key name (e.g. 'enter', 'ctrl+c')"}
            },
            "required": ["action"]
        }
    },

    # ===== WEB TOOLS =====
    {
        "name": "web_search",
        "description": "Performs a real web search to get up-to-date information. Use 'deep' mode for comprehensive research.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query"},
                "num_results": {"type": "INTEGER", "description": "Number of results (default: 5)"},
                "search_depth": {
                    "type": "STRING", 
                    "enum": ["basic", "deep"], 
                    "description": "Search depth. 'basic' for quick results (DDG), 'deep' for comprehensive research (Tavily)."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "visit_webpage",
        "description": "Scrapes the text content of a webpage URL.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {"type": "STRING", "description": "URL to visit"}
            },
            "required": ["url"]
        }
    },

    # ===== CLIPBOARD TOOLS =====
    {
        "name": "clipboard_read",
        "description": "Reads text from the system clipboard.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "clipboard_write",
        "description": "Writes text to the system clipboard.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {"type": "STRING", "description": "Text to copy"}
            },
            "required": ["text"]
        }
    },

    # ===== PROACTIVE & LEARNING =====
    {
        "name": "set_reminder",
        "description": "Sets a proactive reminder timer.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "duration_seconds": {"type": "INTEGER", "description": "Seconds to wait"},
                "message": {"type": "STRING", "description": "Message to try_speak when timer ends"}
            },
            "required": ["duration_seconds", "message"]
        }
    },
    {
        "name": "learn_proactive_rule",
        "description": "Teaches Atomik a new behavioral rule based on user feedback (e.g., 'Don't speak when I am coding').",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "rule": {"type": "STRING", "description": "The rule to learn"}
            },
            "required": ["rule"]
        }
    },
    # =========================================================================
    # MCP ARAÇLARI - Memory & Sequential Thinking
    # ARTIK DİNAMİK OLARAK MCP CLIENT TARAFINDAN YÜKLENİYOR
    # =========================================================================

    # ===== VOICE RECORDING TOOLS =====
    {
        "name": "start_voice_recording",
        "description": "Starts recording Atomik's voice output. Call this before speaking a message you want to record.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "stop_voice_recording",
        "description": "Stops recording and saves the audio file. Returns the file path.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "send_voice_whatsapp",
        "description": "Sends the last recorded voice message via WhatsApp to a recipient.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "recipient": {"type": "STRING", "description": "Phone number with country code (e.g., 905551234567) or WhatsApp JID"}
            },
            "required": ["recipient"]
        }
    },

]




