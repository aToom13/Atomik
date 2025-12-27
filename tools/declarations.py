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
    },
    # Clipboard Tools
    {
        "name": "clipboard_read",
        "description": "Panodaki (clipboard) metni oku. Kullanıcı 'kopyaladığım şey' dediğinde kullan.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "clipboard_write",
        "description": "Metni panoya (clipboard) kopyala.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {"type": "STRING", "description": "Panoya kopyalanacak metin"}
            },
            "required": ["text"]
        }
    },
    # Web Search Tool
    {
        "name": "web_search",
        "description": "İnternette arama yap ve sonuçları getir. Güncel bilgi için kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Arama sorgusu"},
                "num_results": {"type": "INTEGER", "description": "Kaç sonuç getirilsin (varsayılan: 5)"}
            },
            "required": ["query"]
        }
    },
    # Notification Tool
    {
        "name": "show_notification",
        "description": "Masaüstü bildirimi göster. Önemli uyarılar veya hatırlatmalar için kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "title": {"type": "STRING", "description": "Bildirim başlığı"},
                "message": {"type": "STRING", "description": "Bildirim mesajı"}
            },
            "required": ["title", "message"]
        }
    },
    # ===== RAG MEMORY TOOLS =====
    {
        "name": "remember_this",
        "description": "Bir konuşmayı veya bilgiyi uzun süreli hafızaya kaydet. Kullanıcı 'bunu hatırla', 'kaydet' dediğinde veya önemli konuşmalar sonunda kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "summary": {
                    "type": "STRING",
                    "description": "Hatırlanacak bilginin özeti (örn: 'Kullanıcı depremler hakkında sordu, AFAD sitesinden baktık')"
                },
                "topic": {
                    "type": "STRING",
                    "description": "Konu etiketi (örn: 'deprem', 'hava', 'proje')"
                }
            },
            "required": ["summary"]
        }
    },
    {
        "name": "recall_memory",
        "description": "Geçmiş konuşmalardan ilgili anıları getir. 'Geçen ne konuşmuştuk?', 'X hakkında ne demiştim?' gibi sorularda kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Aranacak konu veya anahtar kelime"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_recent_memories",
        "description": "Son günlerdeki tüm kayıtlı anıları listele. 'Son zamanlarda ne konuştuk?' sorularında kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "days": {
                    "type": "INTEGER",
                    "description": "Kaç günlük anılar getirilsin (varsayılan: 7)"
                }
            }
        }
    },
    # ===== WEB SCRAPER TOOL =====
    {
        "name": "visit_webpage",
        "description": "Bir web sayfasını ziyaret edip içeriğini oku. Web search sonuçlarından detay almak için kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {
                    "type": "STRING",
                    "description": "Ziyaret edilecek sayfa URL'i"
                }
            },
            "required": ["url"]
        }
    },
    # ===== SESSION HISTORY TOOLS =====
    {
        "name": "search_chat_history",
        "description": "Geçmiş sohbetlerde arama yap. 'X hakkında ne konuşmuştuk?', 'Geçen Y demiştim' gibi sorularda kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Aranacak kelime veya konu"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_chat_stats",
        "description": "Sohbet istatistiklerini göster. Kaç konuşma, kaç mesaj gibi.",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    # ===== CODE QUALITY TOOLS =====
    {
        "name": "run_linter",
        "description": "Python dosyasını lint kontrolünden geçir. Kod kalitesi ve hataları kontrol eder.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {
                    "type": "STRING",
                    "description": "Kontrol edilecek Python dosyasının yolu"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "format_code",
        "description": "Python dosyasını otomatik formatla (black). Kodu güzelleştirir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {
                    "type": "STRING",
                    "description": "Formatlanacak Python dosyasının yolu"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "run_tests",
        "description": "Testleri çalıştır (pytest). Belirli bir dosya veya klasör için.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {
                    "type": "STRING",
                    "description": "Test dosyası veya klasörü (boş bırakılırsa tüm testler)"
                }
            }
        }
    },
    # ===== LEARNING TOOLS =====
    {
        "name": "log_mood",
        "description": "Kullanıcının ruh halini kaydet. Görsel ipuçlarından veya konuşmadan anladığında kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "mood": {
                    "type": "STRING",
                    "description": "Ruh hali: happy, sad, tired, focused, stressed, relaxed, neutral"
                },
                "context": {
                    "type": "STRING",
                    "description": "Bağlam veya neden (opsiyonel)"
                }
            },
            "required": ["mood"]
        }
    },
    {
        "name": "update_preference",
        "description": "Kullanıcı tercihini kaydet. 'Favori X' gibi bilgiler için kullan.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "key": {
                    "type": "STRING",
                    "description": "Tercih anahtarı (örn: favorite_color, favorite_language)"
                },
                "value": {
                    "type": "STRING",
                    "description": "Tercih değeri"
                }
            },
            "required": ["key", "value"]
        }
    },
    {
        "name": "add_project",
        "description": "Kullanıcının çalıştığı projeyi kaydet veya güncelle.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {
                    "type": "STRING",
                    "description": "Proje adı"
                },
                "status": {
                    "type": "STRING",
                    "description": "Durum: active, completed, paused, bug_fixing"
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "open_application",
        "description": "Bir uygulamayı doğrudan başlatır. Görsel arama yapmadan hızlıca açar. Örn: 'zen', 'spotify', 'terminal', 'youtube', 'gmail', veya 'https://...' linki.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Uygulama adı veya URL (zen, firefox, spotify, youtube, gmail, vpn_tr, https://...)"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "inspect_web_page",
        "description": "Aktif web sayfasındaki tıklanabilir elemanları (DOM) ve koordinatlarını listeler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "port": {
                    "type": "INTEGER",
                    "description": "Debug portu (Varsayılan: 9222)",
                    "default": 9222
                }
            }
        }
    }
]

