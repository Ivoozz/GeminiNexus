#!/bin/bash

# GeminiNexus One-Line Installer
echo "🚀 Start installatie van GeminiNexus op Debian LXC..."

# 1. Systeem pakketten installeren
echo "📦 Systeem updaten en afhankelijkheden installeren..."
sudo apt update && sudo apt install -y python3-pip python3-venv git curl

# 2. Project ophalen (indien nog niet aanwezig)
if [ ! -d "backend" ]; then
    echo "📂 Project bestanden ophalen van GitHub..."
    # De gebruiker moet hier hun eigen repo URL invullen of we gaan ervan uit dat ze al in de map zitten
    # git clone https://github.com/jouw-gebruikersnaam/GeminiNexus.git .
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
echo "1. Vul je .env bestand in."
echo "2. Start de applicatie:"
echo "   source venv/bin/activate"
echo "   python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
echo "------------------------------------------------"
