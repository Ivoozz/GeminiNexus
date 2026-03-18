#!/bin/bash

# GeminiNexus Fully Autonomous Installer (Secure Edition)
echo "🚀 Start installatie van GeminiNexus op Debian LXC..."

# 1. Root check
if [ "$EUID" -ne 0 ]; then 
  echo "❌ Fout: Voer dit script uit als root."
  exit 1
fi

# 2. Bepaal de juiste installatie map
CURRENT_DIR_NAME=$(basename "$(pwd)")
if [ "$CURRENT_DIR_NAME" == "GeminiNexus" ]; then
    INSTALL_DIR=$(pwd)
else
    INSTALL_DIR="$(pwd)/GeminiNexus"
fi

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
    cd "$INSTALL_DIR" || exit 1
else
    if [ "$CURRENT_DIR_NAME" != "GeminiNexus" ]; then
        cd "$INSTALL_DIR" || exit 1
    fi
    echo "📂 Map bestaat al. Laatste wijzigingen ophalen..."
    git fetch --all && git reset --hard origin/main
fi

# 5. Python omgeving opzetten
echo "🐍 Python virtual environment aanmaken..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. Automatische Beveiliging Configuratie
echo "🔐 Beveiliging configureren..."

# Genereer SECRET_KEY als deze nog niet bestaat
if [ ! -f ".env" ]; then
    cp .env.example .env
    RANDOM_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=$RANDOM_SECRET/" .env
    echo "✅ Unieke SECRET_KEY gegenereerd."
fi

# Vraag om wachtwoord en genereer hash (Veilige methode)
if ! grep -q "PASSWORD_HASH=\$2b\$" .env; then
    echo "------------------------------------------------"
    echo "Stel je toegangswachtwoord in voor de webinterface."
    # Gebruik -r om te voorkomen dat backslashes worden geïnterpreteerd
    read -rs -p "Voer wachtwoord in: " plain_pwd
    echo ""
    read -rs -p "Bevestig wachtwoord: " confirm_pwd
    echo ""
    
    if [ "$plain_pwd" == "$confirm_pwd" ] && [ ! -z "$plain_pwd" ]; then
        echo "⏳ Wachtwoord hashen..."
        # Geef het wachtwoord door via een environment variable om shell expansion te voorkomen
        export TEMP_PWD="$plain_pwd"
        PWD_HASH=$(python3 -c "import bcrypt, os; print(bcrypt.hashpw(os.environ['TEMP_PWD'].encode(), bcrypt.gensalt()).decode())")
        unset TEMP_PWD
        
        # Ontsnap de $ tekens voor sed
        ESCAPED_HASH=$(echo $PWD_HASH | sed 's/\$/\\\$/g')
        sed -i "s|PASSWORD_HASH=.*|PASSWORD_HASH=$ESCAPED_HASH|" .env
        echo "✅ Wachtwoord veilig gehashed en opgeslagen."
    else
        echo "⚠️  Wachtwoorden komen niet overeen of zijn leeg. Probeer de installatie opnieuw."
        exit 1
    fi
fi

# 7. Systemd Service
echo "------------------------------------------------"
read -p "❓ Wil je een autostart service aanmaken? (j/n): " create_service
if [[ $create_service == "j" || $create_service == "J" ]]; then
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
    echo "✅ Service 'gemininexus' is actief."
fi

echo ""
echo "✅ GeminiNexus installatie voltooid!"
echo "------------------------------------------------"
echo "URL: http://$(hostname -I | awk '{print $1}'):8000"
echo "------------------------------------------------"
