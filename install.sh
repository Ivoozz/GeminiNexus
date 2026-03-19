#!/bin/bash

# GeminiNexus One-Click Installer
echo "🚀 Start installatie van GeminiNexus op Debian LXC..."

# 1. Root check
if [ "$EUID" -ne 0 ]; then 
  echo "❌ Fout: Voer dit script uit als root."
  exit 1
fi

# Functie om te wachten op APT lock
wait_for_apt_lock() {
    while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || fuser /var/lib/apt/lists/lock >/dev/null 2>&1 || fuser /var/lib/dpkg/lock >/dev/null 2>&1; do
        echo "⏳ Wachten op APT lock..."
        sleep 1
    done
}

# 2. Systeem pakketten installeren
wait_for_apt_lock
echo "📦 Voorbereiden van systeem..."
apt update && apt install -y python3-pip python3-venv git curl psmisc

# 3. Project ophalen
if [ ! -d "GeminiNexus" ]; then
    git clone https://github.com/Ivoozz/GeminiNexus.git
    cd GeminiNexus || exit 1
else
    cd GeminiNexus || exit 1
    git fetch --all && git reset --hard origin/main
fi

INSTALL_DIR=$(pwd)

# 4. Python omgeving opzetten
echo "🐍 Python omgeving opzetten..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Basis .env aanmaken (zonder hash, zodat onboarding getoond wordt)
if [ ! -f .env ]; then
    RANDOM_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    echo "SECRET_KEY=$RANDOM_SECRET" > .env
fi

# 6. Systemd Service aanmaken en starten
echo "⚙️  Service configureren..."
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
systemctl restart gemininexus

echo ""
echo "✅ GeminiNexus is succesvol geïnstalleerd en draait!"
echo "------------------------------------------------"
echo "Open je browser op: http://$(hostname -I | awk '{print $1}'):8000"
echo "Volg de instructies op het scherm voor de onboarding."
echo "------------------------------------------------"
