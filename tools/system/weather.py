"""
Weather Tool for Atomik
Uses OpenWeatherMap API
"""
import os
import requests
from dotenv import load_dotenv

# Load env
load_dotenv()

# Also try parent directories
import pathlib
for parent in pathlib.Path(__file__).parents:
    env_file = parent / ".env"
    if env_file.exists():
        _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        load_dotenv(os.path.join(_project_root, ".env"))
        break


def get_weather(city: str) -> str:
    """
    Get current weather for a city.
    
    Args:
        city: City name (e.g., "Istanbul", "Ankara")
    
    Returns:
        Weather report string
    """
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return "❌ OPENWEATHERMAP_API_KEY bulunamadı. .env dosyasına ekleyin."
    
    base_url = "http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric",
        "lang": "tr"
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        data = response.json()
        
        if response.status_code == 200:
            weather_desc = data["weather"][0]["description"]
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]
            
            return (
                f"🌍 {city.title()} Hava Durumu: "
                f"{temp:.0f}°C ({weather_desc}), "
                f"Hissedilen: {feels_like:.0f}°C, "
                f"Nem: %{humidity}, "
                f"Rüzgar: {wind_speed} m/s"
            )
        elif response.status_code == 404:
            return f"❌ Şehir bulunamadı: {city}"
        else:
            return f"❌ Hata: {data.get('message', 'Bilinmeyen hata')}"
            
    except Exception as e:
        return f"❌ Bağlantı hatası: {str(e)}"


# Test
if __name__ == "__main__":
    print(get_weather("Istanbul"))
