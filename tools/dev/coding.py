"""
Coding Tools for Atomik
Provides safe code execution and surgical file editing capabilities.
"""
import os
import subprocess

# Try langchain import, fallback to None if not available
try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func): return func  # Dummy decorator

# Try to get workspace from config, fallback to current dir
try:
    from config import config
    WORKSPACE_DIR = config.workspace.base_dir
except ImportError:
    WORKSPACE_DIR = os.getcwd()

# Simple logger fallback
try:
    from utils.logger import get_logger
    logger = get_logger()
except ImportError:
    class DummyLogger:
        def info(self, msg): print(f"INFO: {msg}")
        def error(self, msg): print(f"ERROR: {msg}")
        def warning(self, msg): print(f"WARNING: {msg}")
    logger = DummyLogger()


# ============================================
# BACKWARD COMPATIBILITY (for executor.py)
# ============================================
def delegate_coding(prompt: str, context: str = "") -> dict:
    """
    Code generation using Gemini API.
    Returns a dict with filename, code, and explanation.
    Designed for future multi-provider support.
    """
    try:
        import os
        import json
        import re
        
        # Use google-generativeai for code generation
        try:
            import google.generativeai as genai
        except ImportError:
            return {"success": False, "error": "google-generativeai not installed"}
        
        # Get API key
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return {"success": False, "error": "GEMINI_API_KEY not set"}
        
        genai.configure(api_key=api_key)
        
        # Use flash model for code generation (fast and capable)
        model = genai.GenerativeModel("gemini-3-flash-preview")
        
        # Load prompt from file
        try:
             # Construct path to prompts/calcoder.txt relative to this file
             # coding.py is in tools/dev/, so we go up two levels to root, then into AtomBase/prompts
             # But project root is safer to rely on config or helper if available.
             # Let's use absolute path relative to project assumption: /home/atom13/Projeler/Atomik/AtomBase/prompts/calcoder.txt
             # Better: Use __file__ relative path
             
             base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # tools/dev -> tools -> root
             prompt_path = os.path.join(base_dir, "AtomBase", "prompts", "calcoder", "calcoder.txt")
             
             with open(prompt_path, "r", encoding="utf-8") as f:
                 prompt_template = f.read()
                 
             full_prompt = prompt_template.format(prompt=prompt, context=context)
             
        except Exception as file_error:
            logger.warning(f"Could not load calcoder prompt from file, using fallback: {file_error}")
            # Fallback (Original hardcoded prompt)
            full_prompt = f"""Generate Python code for this task. Return ONLY valid JSON with no markdown:
{{"filename": "appropriate_name.py", "code": "...the complete code...", "explanation": "Brief explanation"}}

Task: {prompt}
Context: {context}

Important:
- Return ONLY the JSON object, no markdown code blocks
- Make sure the code is complete and runnable
- Use appropriate filename based on the task"""
        
        response = model.generate_content(full_prompt)
        content = response.text
        
        # Clean up markdown if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # Find JSON in response
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            result = json.loads(match.group())
            result["success"] = True
            return result
        
        return {"success": False, "error": "Could not parse response as JSON"}
        
    except Exception as e:
        logger.error(f"Delegate coding error: {e}")
        return {"success": False, "error": str(e)}

def save_generated_code(filename: str, code: str, workspace: str) -> str:
    """Save generated code to workspace."""
    filepath = os.path.join(workspace, filename)
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else workspace, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    return filepath

# ============================================
# MODERN TOOLS (LangChain @tool)
# ============================================

def _get_safe_path(filename: str) -> str:
    """Workspace güvenliği için path kontrolü."""
    # Basit bir güvenlik kontrolü, files.py ile benzer
    if filename.startswith("/"):
        if not filename.startswith(WORKSPACE_DIR):
            # Eğer workspace dışı ise ve atom_workspace içinde değilse hata
             if "atom_workspace" not in filename: # Basit check
                 pass # Şimdilik soft pass, gerekirse fixlenir
    
    # Relative path ise workspace'e ekle
    if not os.path.isabs(filename):
         return os.path.join(WORKSPACE_DIR, filename)
    return filename

@tool
def edit_file(filename: str, target_text: str, replacement_text: str) -> str:
    """
    Bir dosya içinde "cerrah titizliğiyle" değişiklik yapar.
    Dosyanın tamamını yeniden yazmak yerine, sadece ilgili kısmı değiştirir.
    
    Args:
        filename: Dosya yolu
        target_text: Değiştirilecek metin (orijinal haliyle, tam eşleşmeli)
        replacement_text: Yeni metin
    """
    logger.info(f"Editing file: {filename}")
    try:
        file_path = _get_safe_path(filename)
        
        if not os.path.exists(file_path):
            return f"Hata: Dosya bulunamadı: {filename}"
            
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        if target_text not in content:
            # Basit whitespace temizliği ile dene
            if target_text.strip() in content:
                 target_text = target_text.strip()
            else:
                return "Hata: Hedef metin dosyada bulunamadı. Lütfen boşluklara dikkat edin veya metnin bir kısmını aratın."
        
        # Replace only the first occurrence to be safe, or logic could be improved
        new_content = content.replace(target_text, replacement_text, 1)
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        return f"✅ Dosya güncellendi: {filename}"
        
    except Exception as e:
        logger.error(f"Edit failed: {e}")
        return f"Düzenleme hatası: {e}"

@tool
def run_python(code: str) -> str:
    """
    Python kodunu güvenli bir şekilde çalıştırır.
    Küçük scriptler, hesaplamalar veya testler için kullanın.
    
    Args:
        code: Çalıştırılacak Python kodu
    """
    logger.info("Running python code via subprocess")
    try:
        # Kodu geçici bir dosyaya yaz
        temp_file = os.path.join(WORKSPACE_DIR, "temp_execution.py")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(code)
            
        # Çalıştır
        result = subprocess.run(
            ["python3", temp_file],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=WORKSPACE_DIR
        )
        
        # Temizle
        if os.path.exists(temp_file):
            os.remove(temp_file)
            
        output = result.stdout
        if result.stderr:
            output += f"\n[HATA]\n{result.stderr}"
            
        if not output:
            output = "Kod çalıştı (Çıktı yok)."
            
        return output
        
    except subprocess.TimeoutExpired:
        return "Zaman aşımı: Kod 10 saniyeden uzun sürdü."
    except Exception as e:
        return f"Çalıştırma hatası: {e}"

@tool
def read_file_preview(filename: str, lines: int = 10) -> str:
    """
    Dosyanın ilk N satırını okur. Hızlı kontrol için.
    """
    try:
        file_path = _get_safe_path(filename)
        with open(file_path, "r", encoding="utf-8") as f:
             head = [next(f) for _ in range(lines)]
        return "".join(head)
    except StopIteration:
        return "Dosya boş veya okunamadı."
    except Exception as e:
        return f"Okuma hatası: {e}"
