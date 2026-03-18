#!/bin/bash

# GeminiNexus Absolute Installer
echo "🚀 Start installatie van GeminiNexus op Debian LXC..."

# 1. Root check
if [ "$EUID" -ne 0 ]; then 
  echo "❌ Fout: Voer dit script uit als root."
  exit 1
fi

# 2. Bepaal installatiepad (standaard in de huidige map, in een submap GeminiNexus)
BASE_DIR=$(pwd)
INSTALL_DIR="$BASE_DIR/GeminiNexus"

# Functie om te wachten op APT lock
wait_for_apt_lock() {
    echo "⏳ Wachten op APT lock..."
    while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || fuser /var/lib/apt/lists/lock >/dev/null 2>&1 || fuser /var/lib/dpkg/lock >/dev/null 2>&1; do
        sleep 1
    done
}

# 3. Systeem pakketten
wait_for_apt_lock
echo "📦 Installeren van systeem afhankelijkheden..."
apt update && apt install -y python3-pip python3-venv git curl psmisc

# 4. Project ophalen of updaten
if [ ! -d "$INSTALL_DIR" ]; then
    echo "📂 Project downloaden van GitHub naar $INSTALL_DIR..."
    git clone https://github.com/Ivoozz/GeminiNexus.git "$INSTALL_DIR" || { echo "❌ Git clone mislukt!"; exit 1; }
else
    echo "📂 Project bestaat al in $INSTALL_DIR, we halen de nieuwste versie op..."
    cd "$INSTALL_DIR" || exit 1
    git fetch --all && git reset --hard origin/main
fi

# Ga naar de projectmap
cd "$INSTALL_DIR" || { echo "❌ Kan de projectmap niet betreden!"; exit 1; }
echo "📍 Huidige map: $(pwd)"

# 5. Python omgeving opzetten
echo "🐍 Python virtual environment aanmaken..."
python3 -m venv venv
source venv/bin/activate

echo "📦 Python pakketten installeren..."
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "❌ FOUT: requirements.txt niet gevonden in $(pwd)!"
    exit 1
fi

# 6. .env setup
if [ ! -f .env ]; then
    echo "⚙️ .env bestand aanmaken..."
    cp .env.example .env
fi

# 7. Systemd Service
echo "------------------------------------------------"
read -p "❓ Wil je een autostart service aanmaken? (j/n): " create_service
if [[ $create_service == "j" || $create_service == "J" ]]; then
    SERVICE_FILE="/etc/systemd/system/gemininexus.service"
    echo "⚙️  Service aanmaken in $SERVICE_FILE..."
    
    cat <<EOF > $SERVICE_FILE
[Unit]
Description=GeminiNexus AI Assistant
After=network.target

[Service]
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable gemininexus
    echo "✅ Service 'gemininexus' ingeschakeld."
fi

echo ""
echo "✅ GeminiNexus installatie voltooid!"
echo "------------------------------------------------"
echo "Locatie: $INSTALL_DIR"
echo "1. Vul je .env bestand in: nano $INSTALL_DIR/.env"
echo "2. Start de service: systemctl start gemininexus"
echo "------------------------------------------------"
