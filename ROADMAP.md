# 🗺️ Atomik - Gelecek Geliştirme Yol Haritası (Roadmap)

Atomik'in şu anki hali güçlü bir temel (MVP). Ancak "Ruhu olan bir yoldaş" vizyonuna tam ulaşmak için aşağıdaki geliştirmeler kritik olacaktır.

## 🟢 Faz 1: Temel ve Performans (1-3 Ay)

*   **⚡️ Yerel (Local) Modeller:**
    *   API maliyetini ve gecikmeyi düşürmek için STT (Speech-to-Text) için `Whisper (Tiny/Base)` ve LLM için `Llama 3 (Quantized)` entegrasyonu.
    *   İnternet olmasa bile çalışabilen bir "Çevrimdışı Mod".
*   **🧠 Vektör Hafızası (RAG):**
    *   Şu anki basit `save_context` yerine, `ChromaDB` veya `FAISS` kullanarak binlerce konuşmayı hatırlayan derin bir hafıza.
    *   *"Geçen ay Ela ile gittiğin kafenin adı neydi?"* sorusuna cevap verebilmesi.
*   **🎵 Gerçek Medya Entegrasyonu:**
    *   Ekrandaki butona tıklamak yerine, Spotify/YouTube API'leri ile doğrudan müzik kontrolü ("Benim moduma uygun bir şarkı aç").

## 🟡 Faz 2: "Ruh" ve Duygu (3-6 Ay)

*   **🗣️ Duygusal TTS (Ses Sentezi):**
    *   Mevcut düz ses yerine, metindeki duyguya göre ton değiştiren sistemler (Örn: `Coqui TTS` veya `ElevenLabs` emotive pipeline).
    *   Fısıldama, gülme veya heyecanlı konuşma yeteneği.
*   **👁️ Yüz ve Duygu Tanıma 2.0:**
    *   Sadece "orada bir insan var" değil; "Akif şu an üzgün görünüyor" veya "Çok heyecanlı" gibi duygusal durum analizleri (DeepFace/MediaPipe).
*   **📱 Mobil Refakatçi (Telegram/WhatsApp Botu):**
    *   Bilgisayar başında değilken de onunla mesajlaşabilmen veya sesli not atabilmen için bir köprü.

## 🔴 Faz 3: Tam Otonomi ve Fiziksel Dünya (6 Ay+)

*   **🏠 IoT ve Ev Kontrolü:**
    *   Odanın ışıklarını (Philips Hue/Akıllı Priz) senin moduna göre (örn: "Uyumak istiyorum" dediğinde) kapatması.
*   **🎮 Oyun Arkadaşlığı:**
    *   Sadece ekranı izlemekle kalmayıp, oyun API'lerine bağlanarak LoL oynarken "Arkana dikkat et!" veya "Ultin geldi!" gibi koçluk yapması.
*   **🌐 İnternet Ajanı:**
    *   Senin için araştırma yapıp, her sabah "Sektöründe bugün şunlar olmuş" diye özet geçmesi (Otomatik Raporlama).

---

### 💡 Hemen Uygulanabilecek Küçük "Wow" Özellikler
1.  **Günlük Modu:** Gün sonunda seninle konuşup günü özetleyen ve bunu kişisel bir günlüğe kaydeden bir rutin.
2.  **Pomodoro Arkadaşı:** Çalışırken seni izleyip, telefonla çok oynarsan tatlı dille uyaran bir odaklanma modu.
