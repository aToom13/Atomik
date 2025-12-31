#!/bin/bash
# Atomik Virtual Workspace - Startup Script
# Bu script Atomik'in bağımsız çalışma alanını başlatır

RESOLUTION="1888x1041"
VNC_PORT=5900
VIRTUAL_DISPLAY=":99"

echo "🚀 Atomik Virtual Workspace başlatılıyor..."

# Önceki süreçleri temizle
pkill -f "Xvfb $VIRTUAL_DISPLAY" 2>/dev/null
pkill x11vnc 2>/dev/null
pkill remmina 2>/dev/null
sleep 0.5

# 1. Sanal ekranı başlat
echo "📺 Sanal ekran başlatılıyor ($RESOLUTION)..."
Xvfb $VIRTUAL_DISPLAY -screen 0 ${RESOLUTION}x24 &

# X sunucusunun hazır olmasını bekle
echo "⏳ X sunucusu bekleniyor..."
for i in {1..10}; do
    if xdpyinfo -display $VIRTUAL_DISPLAY > /dev/null 2>&1; then
        echo "✅ X sunucusu hazır!"
        break
    fi
    sleep 0.5
done

# 1.5. Window manager başlat (pencere maximize için gerekli)
echo "🪟 Window manager başlatılıyor..."
DISPLAY=$VIRTUAL_DISPLAY openbox &
sleep 0.5

# 🔊 Sistem sesini (Beep/Bell) kapat - HEM SANAL HEM ANA EKRAN
echo "🔇 Sistem 'ding' sesleri kapatılıyor..."
DISPLAY=$VIRTUAL_DISPLAY xset b off 2>/dev/null
DISPLAY=$VIRTUAL_DISPLAY xset b 0 0 0 2>/dev/null
# Ana ekran için de kapat (Remmina üzerinden gelen sesler için)
xset b off 2>/dev/null
xset b 0 0 0 2>/dev/null


# 2. VNC sunucusunu başlat
echo "🔗 VNC sunucusu başlatılıyor (port $VNC_PORT)..."
# -forever: bağlantı kopsa da dinlemeye devam et
# -loop: sunucu kapanırsa yeniden başlat
# -bg KULLANMA (loop ile çakışır), onun yerine & kullan
# Wayland detected hatasını önlemek için WAYLAND_DISPLAY'i siliyoruz ve XDG_SESSION_TYPE=x11 yapıyoruz
mkdir -p /tmp/atomik_logs
env -u WAYLAND_DISPLAY XDG_SESSION_TYPE=x11 x11vnc -display $VIRTUAL_DISPLAY -rfbport $VNC_PORT -nopw -forever -shared -xkb -loop -o /tmp/atomik_logs/x11vnc.log &

# VNC portunun hazır olmasını bekle

# VNC portunun hazır olmasını bekle
echo "⏳ VNC portunun açılması bekleniyor..."
for i in {1..10}; do
    if netstat -tuln | grep ":$VNC_PORT " > /dev/null; then
        echo "✅ VNC portu aktif!"
        break
    fi
    sleep 0.5
done

# 3. Remmina'yı başlat ve tam ekran yap
echo "🖥️  Remmina başlatılıyor..."
# No-kiosk mode, full control
remmina -c vnc://localhost:$VNC_PORT &
sleep 2

# 4. Remmina'yı bul ve yönet
REMMINA_WIN=$(wmctrl -l | grep -i "Remmina" | head -n 1 | awk '{print $1}')

# Eğer Remmina ana penceresi ise (bağlantı penceresi değil), doğru pencereyi bulmaya çalış
# Genellikle başlıkta VNC adresi olur
if [ -z "$REMMINA_WIN" ]; then
    sleep 1
    REMMINA_WIN=$(wmctrl -l | grep "localhost:$VNC_PORT" | awk '{print $1}')
fi

if [ -n "$REMMINA_WIN" ]; then
    # Tam ekran yap
    wmctrl -i -r $REMMINA_WIN -b add,fullscreen
    sleep 0.3
    # 2. masaüstüne taşı
    wmctrl -i -r $REMMINA_WIN -t 1
    sleep 0.3
    # Kullanıcıyı 1. masaüstüne geri getir
    wmctrl -s 0
    echo "✅ Remmina 2. masaüstünde tam ekran açıldı!"
else
    echo "⚠️  Remmina penceresi bulunamadı"
fi

echo ""
echo "🎉 Atomik Virtual Workspace hazır!"
echo "   - Sanal ekran: DISPLAY=$VIRTUAL_DISPLAY"
echo "   - VNC: localhost:$VNC_PORT"
echo "   - Remmina: 2. masaüstünde tam ekran"
echo ""
echo "Örnek kullanım: DISPLAY=$VIRTUAL_DISPLAY gedit &"
