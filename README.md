# Atomik ⚛️

**Atomik**, sıradan bir sesli asistan değil, **"Ruhu Olan Dijital Bir Yoldaş"**tır. Sadece komutları yerine getirmekle kalmaz, ekranınızı görür, bilgisayarınızı kontrol eder ve sizinle doğal, samimi bir ses tonuyla sohbet eder. 

## 🌟 Öne Çıkan Özellikler

### 🔴 Offline Mod (YENİ!)
- **Tamamen yerel çalışma** - İnternet bağlantısı gerektirmez
- **Yerel LLM (Ollama)** - Gemma3 ile hızlı yanıtlar
- **Yerel STT/TTS** - Whisper + Piper ile sesli iletişim
- **Akıllı Araç Yönlendirme** - LLM tabanlı intent sınıflandırma

### 🎙️ Doğal Sesli İletişim
- Metin tabanlı değil, tamamen sesli ve akıcı iletişim
- "Şey...", "Hımm..." gibi insani dolgular

### 👁️ Görsel Farkındalık
- **Ekran Analizi** - OCR + element detection
- **Akıllı Tıklama** - Renk, konum ve metin ile hedef bulma
- **Bölge Tabanlı Kontrol** - "sağ alttaki butona tıkla"

### 💻 Bilgisayar Kontrolü
- Fare ve klavye kontrolü
- Uygulama açma/kapatma
- Dosya oluşturma, okuma, düzenleme
- **Akıllı Kod Üretimi** - "Flappy Bird oyunu yap" → Python kodu

### 🧠 Hafıza Sistemi
- Working Memory (kısa süreli)
- Episodic Memory (olaylar)
- Semantic Memory (bilgi)

## 🚀 Kurulum

```bash
# Depoyu klonla
git clone https://github.com/aToom13/Atomik.git
cd Atomik

# Gereksinimleri yükle
pip install -r requirements.txt

# Ollama kur (offline mod için)
# https://ollama.com/download
ollama pull gemma3:4b
```

## ⚡ Çalıştırma

### Online Mod (Gemini API)
```bash
python main.py
```

### Offline Mod (Yerel LLM)
```bash
python main.py --offline
```

## 📁 Proje Yapısı

```
Atomik/
├── main.py              # Ana giriş noktası
├── AtomBase/            # Sistem çekirdeği
│   └── prompts/         # Sistem promptları
├── audio/               # Ses modülleri
│   ├── loop.py          # Online ses döngüsü
│   └── local_loop.py    # Offline ses döngüsü
├── core/                # Çekirdek modüller
│   ├── offline/         # Offline sistem
│   │   ├── tools.py     # Offline araçlar
│   │   ├── intent.py    # Intent sınıflandırma
│   │   └── llm_client.py # Ollama client
│   └── connection.py    # Bağlantı yönetimi
├── tools/               # Araç modülleri
│   ├── vision/          # OCR, element detection
│   ├── llm/             # LLM router
│   ├── audio/           # STT/TTS
│   └── memory/          # Hafıza sistemi
└── tests/               # Test suite
```

## 🧪 Testler

```bash
python -m pytest tests/ -v
```

## 📝 Offline Araçlar

| Araç          | Açıklama                         | Örnek Komut                 |
| ------------- | -------------------------------- | --------------------------- |
| Dosya Oluştur | LLM ile akıllı dosya/kod üretimi | "Flappy Bird oyunu yap"     |
| Dosya Oku     | Workspace'teki dosyaları oku     | "test.py dosyasını oku"     |
| Tıkla         | Akıllı element bulma ve tıklama  | "mavi butona tıkla"         |
| Uygulama Aç   | Sistem uygulamalarını başlat     | "Terminal aç"               |
| Hatırlatıcı   | Hatırlatıcı ekle/listele         | "yarın toplantıyı hatırlat" |
| Tarih/Saat    | Güncel tarih ve saat             | "saat kaç"                  |

## 🔧 Gereksinimler

- Python 3.10+
- Ollama (offline mod)
- PyAudio, OpenCV, EasyOCR
- PyAutoGUI (bilgisayar kontrolü)

## 📜 Lisans

MIT License
