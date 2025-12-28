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
sleep 1

# 1.5. Window manager başlat (pencere maximize için gerekli)
echo "🪟 Window manager başlatılıyor..."
DISPLAY=$VIRTUAL_DISPLAY openbox &
sleep 0.5

# 🔊 Sistem sesini (Beep/Bell) kapat
echo "🔇 Sistem 'ding' sesleri kapatılıyor..."
DISPLAY=$VIRTUAL_DISPLAY xset b off 2>/dev/null
DISPLAY=$VIRTUAL_DISPLAY xset b 0 0 0 2>/dev/null


# 2. VNC sunucusunu başlat
echo "🔗 VNC sunucusu başlatılıyor (port $VNC_PORT)..."
x11vnc -display $VIRTUAL_DISPLAY -rfbport $VNC_PORT -bg -nopw -forever -shared -xkb 2>/dev/null

# 3. Remmina'yı başlat ve tam ekran yap
echo "🖥️  Remmina başlatılıyor..."
remmina -c vnc://localhost:$VNC_PORT &
sleep 2

# 4. Remmina'yı tam ekran yap
REMMINA_WIN=$(wmctrl -l | grep "localhost:$VNC_PORT" | awk '{print $1}')
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
