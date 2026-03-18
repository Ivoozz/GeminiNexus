#!/bin/bash

# GeminiNexus One-Line Installer
echo "🚀 Start installatie van GeminiNexus op Debian LXC..."

# 1. Check if running as root
if [ "$EUID" -ne 0 ]; then 
  echo "❌ Fout: Voer dit script uit als root (sudo) om de autostart service aan te maken."
  exit 1
fi

# Functie om te wachten op APT lock
wait_for_apt_lock() {
    echo "⏳ Wachten op APT lock (andere installaties)..."
    while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || fuser /var/lib/apt/lists/lock >/dev/null 2>&1 || fuser /var/lib/dpkg/lock >/dev/null 2>&1; do
        sleep 1
    done
    echo "✅ APT lock vrijgegeven."
}

# 2. Systeem pakketten installeren
wait_for_apt_lock
echo "📦 Systeem updaten en afhankelijkheden installeren..."
apt update && apt install -y python3-pip python3-venv git curl psmisc

# 3. Project ophalen
INSTALL_DIR=$(pwd)
if [ ! -d "GeminiNexus" ]; then
    echo "📂 Project bestanden ophalen van GitHub..."
    git clone https://github.com/Ivoozz/GeminiNexus.git
    cd GeminiNexus || exit 1
    INSTALL_DIR=$(pwd)
else
    echo "📂 GeminiNexus map bestaat al, we gaan verder in deze map..."
    cd GeminiNexus || exit 1
    INSTALL_DIR=$(pwd)
fi

# 4. Python omgeving opzetten
echo "🐍 Python virtual environment aanmaken..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Configuratie voorbereiden
if [ ! -f .env ]; then
    echo "⚙️ .env bestand aanmaken..."
    cp .env.example .env
    echo "⚠️  BELANGRIJK: Vergeet niet je wachtwoord hash te genereren met:"
    echo "   python3 scripts/setup_password.py"
fi

# 6. Autostart Service (Systemd)
echo "------------------------------------------------"
read -p "❓ Wil je een autostart service aanmaken? (j/n): " create_service
if [[ $create_service == "j" || $create_service == "J" ]]; then
    echo "⚙️  Systeem service aanmaken..."
    
    SERVICE_FILE="/etc/systemd/system/gemininexus.service"
    
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
    echo "✅ Service 'gemininexus' is aangemaakt en ingeschakeld."
    echo "   Start de service met: systemctl start gemininexus"
fi

echo ""
echo "✅ GeminiNexus is succesvol geïnstalleerd!"
echo "------------------------------------------------"
echo "Volgende stappen:"
echo "1. Ga naar de map: cd $INSTALL_DIR"
echo "2. Vul je .env bestand in (wachtwoord hash, etc)."
echo "3. Start de service: systemctl start gemininexus"
echo "   (of handmatig voor debuggen: source venv/bin/activate && uvicorn backend.main:app --host 0.0.0.0 --port 8000)"
echo "------------------------------------------------"
