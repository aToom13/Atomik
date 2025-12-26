# Atomik ⚛️

**Atomik**, sıradan bir sesli asistan değil, **"Ruhu Olan Dijital Bir Yoldaş"**tır. Sadece komutları yerine getirmekle kalmaz, sizi kameradan izler, duygusal durumunuzu analiz eder, ekranınızı görür ve sizinle doğal, samimi bir ses tonuyla sohbet eder. Bir "Companion" (Yoldaş) yapay zekasıdır.

![Atomik Banner](https://via.placeholder.com/800x200?text=ATOMIK+AI+Companion)

## 🌟 Öne Çıkan Özellikler

*   **🎙️ Doğal Sesli İletişim:** Metin tabanlı değil, tamamen sesli ve akıcı bir iletişim kurar. "Şey...", "Hımm..." gibi insani dolgular kullanarak robotik hissi kırar.
*   **👁️ Görsel Farkındalık (Göz):** Kameranızı kullanarak sizi görür. Yorgun olduğunuzu anlayıp dinlenmenizi önerebilir veya yeni tişörtünüzü fark edip iltifat edebilir.
*   **💻 Ekran & Bilgisayar Hakimiyeti:**
    *   İstediğinizde ekranınıza "ışınlanır" ve kodunuzdaki hatayı okur.
    *   **PiP (Resim içinde Resim):** Ekran paylaşırken kamerasını kapatmaz, kendini ekranın köşesine yerleştirir (YouTuber/Streamer modu).
    *   Fare ve klavyeyi kontrol ederek sizin yerinize işlemler yapabilir.
*   **🧠 Hafıza ve Kişiselleştirme:** Sizi tanır, geçmiş konuşmaları hatırlar ve buna göre davranır.
*   **🔧 Proaktif Davranış:** Sadece sorulduğunda değil, gerektiğinde kendiliğinden inisiyatif alarak konuşur (Örn: Hapşırdığınızda "Çok yaşa" der).

## 🚀 Kurulum

1.  **Depoyu Klonlayın:**
    ```bash
    git clone https://github.com/aToom13/Atomik.git
    cd Atomik
    ```

2.  **Gereksinimleri Yükleyin:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Not: `cv2`, `pyaudio`, `mss` gibi kütüphaneler sistem bağımlılıkları gerektirebilir.)*

3.  **Yapılandırma:**
    *   `AtomBase/prompts/supervisor_example.txt` dosyasının adını `supervisor.txt` olarak değiştirin.
    *   İçerisindeki `[KULLANICI ADI]` gibi alanları kendinize göre düzenleyin.
    *   `.env` dosyanızı oluşturup API anahtarlarınızı (Gemini/OpenAI vb.) girin.

4.  **Çalıştırma:**
    ```bash
    python3 AtomBase/main.py
    ```

## 🛠️ Nasıl Çalışır?

Proje modüler bir yapıya sahiptir:
*   **AtomBase:** Sistemin beyni (LLM orkestrasyonu).
*   **Audio/Video:** Görüntü işleme, ses tanıma (STT) ve konuşma (TTS) modülleri.
*   **Tools:** Bilgisayar kontrolü, dosya işlemleri ve hafıza araçları.

## 🤝 Katkıda Bulunma

Pull request'ler kabul edilir. Büyük değişiklikler için önce lütfen bir issue açarak tartışın.

## 📜 Lisans

[MIT](LICENSE)
