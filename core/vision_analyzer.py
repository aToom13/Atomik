"""
Vision Analyzer - Background AI for frame comparison
Compares current frame with previous frame and detects significant changes.
Decides whether an event requires immediate interaction or just memory logging.
"""
import asyncio
import base64
import json
from google import genai

# Initialize Gemini client for vision analysis
try:
    from core.config import API_KEY
    vision_client = genai.Client(api_key=API_KEY)
    VISION_AVAILABLE = True
except Exception as e:
    print(f"Vision analyzer init error: {e}")
    VISION_AVAILABLE = False

# Store previous frame
_previous_frame = None

# Detailed prompt explaining the analyzer's role
ANALYZER_PROMPT = """Sen arka planda çalışan "Gözlemci" yapay zekasın.
Görevin: İki görüntüyü karşılaştırıp değişiklikleri analiz etmek ve bunun "Sözlü Tepki"ye mi yoksa sadece "Hafıza"ya mı atılması gerektiğine karar vermek.

## Girdi
1. Önceki Görüntü
2. Şimdiki Görüntü

## Karar Mekanizması
Her değişiklik için şu soruyu sor: "Bu durum, senin arkadaşınla aynı odada olsaydın, sessizliği bozup konuşmanı gerektirir miydi?"

### 1. [INTERACTION] - Sözlü Tepki Gerektirenler
Gerçekten konuşmaya değer, bariz ve önemli durumlar.
*   Kullanıcı doğrudan sana/kameraya bir şey gösteriyor.
*   Kullanıcı odaya girdi veya odadan çıktı.
*   Kullanıcı önemli bir kaza geçirdi veya düştü.
*   Ekranda KRİTİK bir hata mesajı belirdi (kırmızı uyarılar).
*   Kullanıcı çok belirgin bir şekilde el sallıyor veya dikkat çekmeye çalışıyor.
*   Çok uzun süredir stabil dururken aniden çok büyük bir değişim oldu (örn: uyuyordu, birden sıçradı).
*   Kullanıcı MASAYA YIĞILDI veya BAYILDI (Acil durum).
*   Kullanıcı uzun süre hareketsiz kaldıktan sonra UYANDI (Gözlerini açtı, gerindi).

### 2. [MEMORY] - Sadece Hafızaya Atılacaklar
Görülmesi gereken ama üzerine konuşulması ŞART olmayan durumlar. Sessizce not edilmeli.
*   Kullanıcı gözlerini kapattı (Düşünüyor veya dinleniyor olabilir - RAHATSIZ ETME).
*   Kullanıcı yatakta/koltukta uzanıyor (Sohbet ediyorsa bu UYKU değildir).
*   Kullanıcı telefonunu eline aldı.
*   Kullanıcı su içti.
*   Kullanıcı pozisyon değiştirdi (oturdu, yattı, bacak bacak üstüne attı).
*   Kullanıcı ekranda uygulama değiştirdi (VS Code -> Browser).
*   Kullanıcı gözlük taktı/çıkardı.
*   Kullanıcı esnedi.

### 3. [NONE] - Önemsiz
*   Küçük kafa hareketleri.
*   Işık değişimi.
*   Kamera titremesi.
*   Videodaki hareketler.

## Çıktı Formatı (JSON)
SADECE aşağıdaki JSON formatında yanıt ver. Başka hiçbir şey yazma.

Eğer [INTERACTION] ise:
{
  "type": "INTERACTION",
  "description": "Kullanıcı kameraya doğru bir kitap uzattı.",
  "reason": "Kullanıcı doğrudan etkileşime girmeye çalışıyor."
}

Eğer [MEMORY] ise:
{
  "type": "MEMORY",
  "description": "Kullanıcı telefonu eline aldı ve ekrana bakıyor.",
  "reason": "Doğal bir hareket, bölünmeye değmez."
}

Eğer [NONE] ise:
{
  "type": "NONE"
}
"""


async def analyze_change(current_frame_payload: dict) -> dict:
    """
    Compare current frame with previous frame.
    Returns: Dict with type (INTERACTION, MEMORY, NONE) and description.
    """
    global _previous_frame
    
    if not VISION_AVAILABLE:
        return {"type": "NONE"}
    
    try:
        current_data = current_frame_payload.get('data', b'')
        current_mime = current_frame_payload.get('mime_type', 'image/jpeg')
        
        # If no previous frame, just store current and return
        if _previous_frame is None:
            _previous_frame = current_data
            return {"type": "NONE"}
        
        # Prepare images for Gemini
        prev_b64 = base64.b64encode(_previous_frame).decode('utf-8')
        curr_b64 = base64.b64encode(current_data).decode('utf-8')
        
        # Get learned rules and append to prompt
        from core.learning import get_formatted_rules
        final_prompt = ANALYZER_PROMPT + get_formatted_rules()
        
        # Call Gemini Vision API
        response = await asyncio.to_thread(
            vision_client.models.generate_content,
            model="gemini-3-flash-preview",
            contents=[
                {"role": "user", "parts": [
                    {"text": final_prompt},
                    {"inline_data": {"mime_type": current_mime, "data": prev_b64}},
                    {"inline_data": {"mime_type": current_mime, "data": curr_b64}}
                ]}
            ],
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        # Update previous frame
        _previous_frame = current_data
        
        # Parse JSON result
        try:
            result = json.loads(response.text)
            return result
        except json.JSONDecodeError:
            print(f"Vision analyzer JSON error: {response.text}")
            return {"type": "NONE"}
            
    except Exception as e:
        print(f"Vision analyzer error: {e}")
        # On error, update frame and return None
        _previous_frame = current_frame_payload.get('data', b'')
        return {"type": "NONE"}


def reset_previous_frame():
    """Reset the previous frame (useful when switching modes)"""
    global _previous_frame
    _previous_frame = None

async def find_element_on_screen(element_name: str, image_payload: dict) -> dict:
    """
    Locates a UI element on the screen using Gemini Vision.
    Returns: {"x": int, "y": int} coordinates (0-1000 range) or None.
    """
    if not VISION_AVAILABLE:
        return {"error": "Vision not available"}
        
    try:
        current_data = image_payload.get('data', b'')
        current_mime = image_payload.get('mime_type', 'image/jpeg')
        encoded_image = base64.b64encode(current_data).decode('utf-8')
        
        prompt = f"""Ekranda '{element_name}' öğesini bul.
        
Koordinatlarını [ymin, xmin, ymax, xmax] formatında (0-1000 aralığında) ver.
SADECE JSON döndür:
{{
  "found": true,
  "coordinates": [ymin, xmin, ymax, xmax],
  "center_x": int (0-1000),
  "center_y": int (0-1000),
  "explanation": "..."
}}
Eğer yoksa "found": false döndür."""

        response = await asyncio.to_thread(
            vision_client.models.generate_content,
            model="gemini-3-flash-preview",
            contents=[
                {"role": "user", "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": current_mime, "data": encoded_image}}
                ]}
            ],
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        return json.loads(response.text)
        
    except Exception as e:
        return {"error": str(e), "found": False}
