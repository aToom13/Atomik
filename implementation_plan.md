# Atomik Projesi - Detaylı Teknik Yol Haritası ve Analiz Raporu

Bu belge, Atomik projesinin mevcut durumunu analiz eder ve kullanıcı arayüzü (UI) geliştirmesi **yapılmadan**, sistemin çekirdek yeteneklerini, stabilitesini ve zekasını artırmaya yönelik detaylı bir teknik yol haritası sunar.

## 1. Mevcut Durum Analizi (Technical Audit)

Projenin kod tabanı (`/home/atom13/Projeler/Atomik`) üzerinde yapılan inceleme sonuçları aşağıdadır:

### ✅ Güçlü Yönler
*   **Modüler Mimari:** `AtomBase` (Orkestrasyon), `core` (State/Config), `audio` (Giriş/Çıkış) ve `tools` (Yetenekler) şeklinde temiz bir sorumluluk ayrımı var.
*   **Robust Audio Loop:** `audio/loop.py` içindeki döngü, API kesintilerine (`1008`, `Timeout`) karşı dirençli. "Auto-Reconnect" ve model fallback mekanizmaları, kesintisiz bir deneyim için kritik öneme sahip ve iyi uygulanmış.
*   **Gelişmiş Hafıza Mimarisi:** `unified_memory.py` dosyası, literatürdeki "Cognitive Architecture" prensiplerine uygun 3 katmanlı (Working, Episodic, Semantic) bir yapı sunuyor.
*   **Multimodal Yetenek:** `unified_vision.py` ile görme yeteneği, tek bir fonksiyona (`see_screen`) indirgenerek basitleştirilmiş ve performansı (Cache) düşünülmüş.

### ⚠️ Tespit Edilen Eksikler ve Riskler
*   **Test Kapsamı Kritik Seviyede Düşük:** `tests/` klasöründe sadece `test_youtube.py` bulunuyor. Projenin kalbi olan Memory, Audio Loop ve Tool Executor test edilmemiş. Bu durum, yeni özellik eklerken sistemi bozma riskini artırıyor.
*   **Offline Bağımlılık:** Sistem şu an tamamen Gemini Live API'ye bağımlı. İnternet kesintisi veya API sorununda asistan tamamen "sağır ve dilsiz" kalıyor. Yerel bir B planı (Fallback) yok.
*   **Dependency Injection Eksikliği:** Araçlar ve modüller birbirine global `state` nesnesi ve doğrudan importlarla bağlı. Bu durum, modülleri izole etmeyi ve test etmeyi zorlaştırıyor.
*   **Yapılandırılmış Loglama Eksikliği:** Hata ayıklama şu an `print` ifadeleri ve basit loglarla yapılıyor. Kompleks asenkron akışları izlemek için structured logging (JSON log) ve tracing eksik.

---

## 2. Stratejik Hedefler

1.  **Sistem Stabilitesi:** Kod değişikliklerinin yan etkisiz olmasını sağlamak (Test Driven Development).
2.  **Süreklilik (Resilience):** İnternet olmadan da temel iletişimi sürdürebilmek.
3.  **Hafıza Derinliği:** Kullanıcıyı sadece "hatırlayan" değil, "tanıyan" bir yapıya geçmek.
4.  **Otonomi:** Kullanıcı müdahalesi olmadan kendi kendini düzelten ve proaktif davranan ajan yapısı.

---

## 3. Uygulama Yol Haritası (Roadmap)

Aşağıdaki fazlar, UI geliştirmesi içermez ve tamamen backend/core odaklıdır.

### Faz 1: Temel Sağlamlaştırma (Stabilite & Test) 🛠️
*Hedef: Güvenle kod geliştirebilecek bir altyapı kurmak.*

- [ ] **Test Altyapısının Kurulması:**
    - `pytest` ve `pytest-asyncio` kurulumu.
    - Gemini API çağrılarını simüle eden "Mock" yapısının oluşturulması (Gerçek kontör harcamadan test).
- [ ] **Kritik Modül Testleri:**
    - `UnifiedMemory` (CRUD işlemleri, TTL süresi, Vektör arama mock).
    - `ProactiveManager` (Zamanlayıcıların doğru çalışıp çalışmadığı).
    - `ToolExecutor` (Araçların doğru parametrelerle çağrılıp çağrılmadığı).
    - Spesifiktüm toolların tek tek testleri.
- [ ] **Kod Kalitesi ve Linting:**
    - `flake8` ve `black` entegrasyonu ile kod standardizasyonu.
    - Type hinting (Tip güvenliği) eksiklerinin tamamlanması.

### Faz 2: Hibrit Zeka (Offline Yetenekler) 🔌
*Hedef: Asistanın internet yokken de "var olmasını" sağlamak.*

- [ ] **Offline Varlık Modülü:**
    - İnternet bağlantısını sürekli kontrol eden bir `ConnectionManager`.
    - Bağlantı koptuğunda devreye girecek "Low-Resource" moduna geçiş.
- [ ] **Yerel STT (Speech-to-Text):**
    - `Whisper` (tiny veya base model) entegrasyonu. İnternet yokken de komutları metne çevirebilme.
- [ ] **Yerel TTS (Text-to-Speech):**
    - Basit bir offline TTS (örn: `pyttsx3` veya `coqui-tts`'in hafif versiyonu) ile "Bağlantım koptu, beklemedeyim" diyebilme.

### Faz 3: Hafıza ve Öğrenme Derinleşmesi 🧠
*Hedef: Asistanın kullanıcıyı gerçekten "tanımasını" sağlamak.*

- [ ] **Otomatik Gerçek Çıkarımı (Fact Extraction):**
    - Konuşma metinlerinden arka planda otomatik bilgi çeken bir analizci.
    - Örn: Kullanıcı "Kedim Boncuk aşı oldu" dediğinde -> `{subject: "Boncuk", type: "Cat", attribute: "Vaccinated"}` bilgisini semantic hafızaya işlemesi.
- [ ] **Duygu Haritası:**
    - Kullanıcının hangi saatlerde, hangi konularda nasıl hissettiğini takip eden bir analitik katmanı.
- [ ] **Vektör Hafıza Optimizasyonu:**
    - ChromaDB sorgularında "tarih filtresi" ve "önem derecesi" (importance score) ekleyerek gereksiz anıların elenmesi.

### Faz 4: Gelişmiş Ajan Yetenekleri (Tools 2.0) ⚡
*Hedef: Asistanın bilgisayar üzerindeki hakimiyetini artırmak.*

- [ ] **Akıllı Kodlama Ajanı (Calcoder Pro v2):**
    - Sadece tek dosya değil, proje genelindeki bağımlılıkları analiz edebilen kodlama yeteneği.
    - Kendi yazdığı kodu çalıştırma ve hata çıktısına göre kendini düzeltme (Self-Healing) döngüsü.
- [ ] **Derin Sistem Kontrolü:**
    - Linux sistem süreçlerini (Process) yönetme, kaynak kullanımını izleme.
    - Uygulama pencerelerini isme göre bulup odaklama ve yönetme.
- [ ] **Proaktif İş Akışları:**
    - "Bilgisayar açıldığında şunu yap", "Spotify açılırsa sesi kıs" gibi kural tabanlı otomasyonlar.

## 4. Öneri: İlk Adım
Bu planı onaylarsanız, **Faz 1: Temel Sağlamlaştırma** ile başlamalıyız. `tests/` klasörünü yapılandırıp, mevcut hafıza sistemini test altına alarak (Unit Tests) ileride yapacağımız değişiklikler için güvenli bir zemin oluşturmalıyız.
