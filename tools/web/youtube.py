"""
Atomik YouTube Video Analyzer Tool
V 1.0
Bu modül, verilen bir YouTube videosunun içeriğini (altyazı ve metadata) analiz eder.
"""

import json
import re
from typing import Dict, Optional, List
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
import yt_dlp
import os

class YouTubeAnalyzer:
    """YouTube videolarını analiz eden sınıf."""
    
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'extract_flat': True,
        }

    def _extract_video_id(self, url: str) -> Optional[str]:
        """URL'den Video ID'sini çıkarır."""
        # Standart URL'ler
        patterns = [
            r'(?:v=|\/)([0-9A-Za-z_-]{11}).*',
            r'(?:youtu\.be\/)([0-9A-Za-z_-]{11})',
            r'(?:embed\/)([0-9A-Za-z_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def get_transcript(self, video_id: str) -> str:
        """Video altyazısını çeker (Türkçe veya İngilizce)."""
        try:
            # Instantiate the API
            ytt_api = YouTubeTranscriptApi()
            
            # Use .list() instead of .list_transcripts()
            transcript_list = ytt_api.list(video_id)
            
            # Öncelik sırası: Türkçe (manuel), İngilizce (manuel), Türkçe (oto), İngilizce (oto)
            try:
                transcript = transcript_list.find_manually_created_transcript(['tr', 'en'])
            except:
                try:
                    transcript = transcript_list.find_generated_transcript(['tr', 'en'])
                except:
                    # Hiçbiri yoksa ilk bulduğunu al ve çevir
                    transcript = transcript_list.find_transcript(['en']) # Varsayılan fallback
            
            # Transcript verisini çek
            data = transcript.fetch()
            
            # Text formatına çevir
            formatter = TextFormatter()
            text_transcript = formatter.format_transcript(data)
            
            return text_transcript
        except Exception as e:
            # Yedek deneme: Belki static method olarak get_transcript vardır (bazı versiyonlar için)
            if "has no attribute 'list'" in str(e):
                try: 
                    # Çok eski yöntem
                    return str(YouTubeTranscriptApi.get_transcript(video_id))
                except:
                    pass
            return f"Altyazı alınamadı: {str(e)}"

    def get_metadata(self, url: str) -> Dict:
        """Video başlığı, açıklama ve diğer bilgileri çeker."""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Bilinmiyor'),
                    'description': info.get('description', ''),
                    'duration': info.get('duration', 0),
                    'author': info.get('uploader', 'Bilinmiyor'),
                    'views': info.get('view_count', 0),
                    'id': info.get('id', '')
                }
        except Exception as e:
            return {'error': str(e)}

    def analyze_video(self, url: str, query: str = None) -> Dict:
        """
        Videoyu analiz eder ve Gemini için hazır hale getirir.
        
        Args:
            url: Video linki
            query: Kullanıcının özel sorusu (opsiyonel)
            
        Returns:
            Dict: Analiz verileri (meta, transcript, prompt_context)
        """
        video_id = self._extract_video_id(url)
        if not video_id:
            return {"error": "Geçersiz YouTube linki"}
        
        print(f"📺 Video Analiz Ediliyor: {video_id}...")
        
        # Metadata ve Transcript çek
        metadata = self.get_metadata(url)
        if 'error' in metadata:
            return {"error": f"Metadata hatası: {metadata['error']}"}
            
        transcript = self.get_transcript(video_id)
        
        # Sonuç paketi
        result = {
            "metadata": metadata,
            "transcript_preview": transcript[:500] + "..." if len(transcript) > 500 else transcript,
            "full_transcript": transcript,
            "query": query
        }
        
        return result

# Singleton instance
_analyzer = YouTubeAnalyzer()

def get_youtube_content(url: str, query: str = None) -> Dict:
    """Executor için wrapper."""
    return _analyzer.analyze_video(url, query)
