"""
Code Delegation Tool - Delegates coding tasks to smarter model
Uses Gemini 3 Flash Preview for complex coding while voice model handles conversation
"""
import os
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
# Also try parent directories for .env
import pathlib
for parent in pathlib.Path(__file__).parents:
    env_file = parent / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        break

# Get API key
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# Smarter model for coding
CODING_MODEL = "gemini-3-flash-preview"

# Initialize client
client = genai.Client(api_key=API_KEY) if API_KEY else None

CODING_SYSTEM_PROMPT = """Sen uzman bir yazılım geliştiricisin.
Görevin:
1. Kullanıcının isteğini analiz et
2. Temiz, çalışan kod yaz
3. Kodu açıkla (kısa ve öz)

Kurallar:
- Kod bloklarını ```language formatında yaz
- Türkçe açıklama yap
- Gereksiz yorum satırı ekleme
- Dosya adı öner (örn: script.py)
"""


def delegate_coding(prompt: str, context: str = "") -> dict:
    """
    Delegates a coding task to a smarter model.
    
    Args:
        prompt: User's coding request
        context: Optional context (current files, etc.)
    
    Returns:
        dict with 'code', 'filename', 'explanation'
    """
    if not client:
        return {
            "success": False,
            "error": "API key not configured",
            "code": "",
            "filename": "",
            "explanation": ""
        }
    
    # Build the full prompt
    full_prompt = f"""
Kullanıcı İsteği: {prompt}

{f"Bağlam: {context}" if context else ""}

Lütfen:
1. İstenen kodu yaz
2. Önerilen dosya adını belirt
3. Kısa bir açıklama yap
"""
    
    try:
        response = client.models.generate_content(
            model=CODING_MODEL,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=CODING_SYSTEM_PROMPT,
                temperature=0.2,
                max_output_tokens=4096
            )
        )
        
        result_text = response.text
        
        # Parse code blocks
        code = ""
        filename = "output.py"
        
        import re
        code_match = re.search(r'```(\w+)?\n(.*?)```', result_text, re.DOTALL)
        if code_match:
            lang = code_match.group(1) or "python"
            code = code_match.group(2).strip()
            
            # Suggest filename based on language
            ext_map = {
                "python": ".py",
                "javascript": ".js",
                "typescript": ".ts",
                "html": ".html",
                "css": ".css",
                "bash": ".sh",
                "shell": ".sh",
                "json": ".json",
                "yaml": ".yaml",
                "sql": ".sql"
            }
            ext = ext_map.get(lang.lower(), ".txt")
            
            # Try to extract filename from response
            filename_match = re.search(r'(?:dosya adı|filename|file)[:\s]+[`"]?(\w+(?:\.\w+)?)[`"]?', result_text, re.IGNORECASE)
            if filename_match:
                filename = filename_match.group(1)
                if not any(filename.endswith(e) for e in ext_map.values()):
                    filename += ext
            else:
                filename = f"code{ext}"
        
        # Get explanation (text outside code blocks)
        explanation = re.sub(r'```.*?```', '', result_text, flags=re.DOTALL).strip()
        # Shorten for voice
        if len(explanation) > 300:
            explanation = explanation[:300] + "..."
        
        return {
            "success": True,
            "code": code,
            "filename": filename,
            "explanation": explanation,
            "full_response": result_text
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "code": "",
            "filename": "",
            "explanation": f"Kod oluşturulurken hata: {e}"
        }


def save_generated_code(filename: str, code: str, workspace_dir: str = None) -> str:
    """Saves generated code to workspace."""
    if not workspace_dir:
        workspace_dir = os.path.join(os.path.dirname(__file__), "atom_workspace")
    
    os.makedirs(workspace_dir, exist_ok=True)
    filepath = os.path.join(workspace_dir, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(code)
    
    return filepath


# Test
if __name__ == "__main__":
    result = delegate_coding("Fibonacci dizisinin ilk 10 elemanını yazdıran bir Python scripti yaz")
    print("Success:", result["success"])
    print("Filename:", result["filename"])
    print("Code:\n", result["code"])
    print("Explanation:", result["explanation"])
