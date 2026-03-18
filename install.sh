#!/bin/bash

# GeminiNexus One-Line Installer
echo "🚀 Start installatie van GeminiNexus op Debian LXC..."

# 1. Systeem pakketten installeren
echo "📦 Systeem updaten en afhankelijkheden installeren..."
sudo apt update && sudo apt install -y python3-pip python3-venv git curl

# 2. Project ophalen
if [ ! -d "GeminiNexus" ]; then
    echo "📂 Project bestanden ophalen van GitHub..."
    git clone https://github.com/Ivoozz/GeminiNexus.git
    cd GeminiNexus || exit
else
    echo "📂 GeminiNexus map bestaat al, we gaan verder in deze map..."
    cd GeminiNexus || exit
fi

# 3. Python omgeving opzetten
echo "🐍 Python virtual environment aanmaken..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configuratie voorbereiden
if [ ! -f .env ]; then
    echo "⚙️ .env bestand aanmaken..."
    cp .env.example .env
    echo "⚠️  BELANGRIJK: Vergeet niet je wachtwoord hash te genereren met:"
    echo "   python3 scripts/setup_password.py"
fi

echo ""
echo "✅ GeminiNexus is succesvol geïnstalleerd!"
echo "------------------------------------------------"
echo "Volgende stappen:"
echo "1. Ga naar de map: cd GeminiNexus"
echo "2. Vul je .env bestand in."
echo "3. Start de applicatie:"
echo "   source venv/bin/activate"
echo "   python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
echo "------------------------------------------------"
