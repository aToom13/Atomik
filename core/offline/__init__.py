"""
Atomik Offline System Core
Yerel (offline) mod için temel bileşenler.

Bu modül şunları içerir:
- OfflineTools: Dosya işlemleri, hatırlatıcılar, sistem bilgisi vb.
- IntentClassifier: LLM tabanlı niyet sınıflandırma
- OllamaClient: Yerel LLM (Ollama) client

Kullanım:
    from core.offline import OfflineTools, get_tool_response, classify_intent
"""

from core.offline.tools import OfflineTools, get_tool_response
from core.offline.intent import IntentClassifier, classify_intent, get_intent_classifier
from core.offline.llm_client import OllamaClient

__all__ = [
    'OfflineTools',
    'get_tool_response',
    'IntentClassifier', 
    'classify_intent',
    'get_intent_classifier',
    'OllamaClient'
]
