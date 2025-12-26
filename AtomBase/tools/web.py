"""
Web Tools for Atomik
Based on AtomAgent's robust web capabilities.
Allows Atomik to research, read pages, and get news.
"""
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from duckduckgo_search import DDGS
from utils.logger import get_logger

logger = get_logger()

# Güvenilir siteler listesi (Opsiyonel filtreleme için)
TRUSTED_DOMAINS = [
    "github.com", "stackoverflow.com", "docs.python.org", "pypi.org",
    "developer.mozilla.org", "w3schools.com", "geeksforgeeks.org",
    "medium.com", "dev.to", "wikipedia.org"
]

def _clean_text(text: str, max_length: int = 1500) -> str:
    """Metni temizler ve kısaltır."""
    text = ' '.join(text.split())
    if len(text) > max_length:
        text = text[:max_length] + "... (devamı kesildi)"
    return text

@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    Internet üzerinde arama yapar.
    Bilgi eksikliği olduğunda veya güncel bilgi gerektiğinde kullanın.
    
    Args:
        query: Arama sorgusu (örn: "python request library usage")
        max_results: Sonuç sayısı (varsayılan 5)
    """
    logger.info(f"Web search: {query}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        
        if not results:
            return "Sonuç bulunamadı."
            
        output = [f"🔍 '{query}' için sonuçlar:\n"]
        for i, r in enumerate(results, 1):
            output.append(f"{i}. {r.get('title', 'Başlık Yok')}")
            output.append(f"   🔗 {r.get('href', '')}")
            output.append(f"   📝 {r.get('body', '')}\n")
        
        output.append("\n💡 Detay için `visit_webpage` kullanabilirsin.")
        return "\n".join(output)
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return f"Arama hatası: {e}"

@tool
def visit_webpage(url: str) -> str:
    """
    Bir web sayfasını ziyaret eder ve içeriğini okur.
    `web_search` sonucundaki linkleri okumak için kullanın.
    
    Args:
        url: Ziyaret edilecek URL
    """
    logger.info(f"Visiting: {url}")
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Gereksiz tagleri temizle
        for tag in soup(["script", "style", "nav", "footer", "iframe", "noscript"]):
            tag.decompose()
            
        # Ana içeriği bulmaya çalış
        main_content = (
            soup.find("main") or 
            soup.find("article") or 
            soup.find("body")
        )
        
        if not main_content:
            main_content = soup
            
        text = main_content.get_text(separator='\n', strip=True)
        cleaned_text = _clean_text(text)
        
        return f"📄 {url}\n\n{cleaned_text}"
        
    except Exception as e:
        logger.error(f"Visit failed: {url} - {e}")
        return f"Sayfa okuma hatası: {e}"

@tool
def get_news(topic: str = "") -> str:
    """
    Güncel haberleri getirir.
    
    Args:
        topic: Haber konusu (boş bırakılırsa genel teknoloji)
    """
    logger.info(f"News: {topic}")
    query = topic if topic else "technology software ai news"
    try:
        with DDGS() as ddgs:
            news = list(ddgs.news(query, max_results=5))
            
        if not news:
            return "Haber bulunamadı."
            
        output = [f"📰 Güncel Haberler ({query}):\n"]
        for n in news:
            output.append(f"• {n.get('title')}")
            output.append(f"  {n.get('date', '')} - {n.get('source', '')}")
            output.append(f"  🔗 {n.get('url')}\n")
            
        return "\n".join(output)
    except Exception as e:
        return f"Haber alma hatası: {e}"
