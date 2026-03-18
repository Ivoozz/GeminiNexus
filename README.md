# GeminiNexus 🚀
**Jouw persoonlijke AI Assistent op Debian LXC, aangedreven door Gemini CLI.**

GeminiNexus is een beveiligde bridge tussen de krachtige Gemini CLI en een moderne webinterface. Het stelt je in staat om via je mobiel (browser) of Telegram je LXC-container te beheren en vragen te stellen aan AI, volledig ontsloten via Cloudflare.

## ✨ Functies
- **Beveiligde Web Interface:** Login met gehashed wachtwoord en JWT-tokens.
- **AI Chat:** Direct praten met Gemini CLI.
- **Systeem Status:** Real-time inzicht in disk- en geheugengebruik.
- **Mobile First:** Geoptimaliseerd voor gebruik op je telefoon.
- **Cloudflare Ready:** Draait op poort 8000, klaar voor `cloudflared`.

## 🔒 Beveiliging (Belangrijk!)
Dit project is ontworpen met security als prioriteit:
1. **Geen Plaintext Wachtwoorden:** Wachtwoorden worden gehashed met `bcrypt`.
2. **JWT Tokens:** Sessies zijn beveiligd met versleutelde tokens.
3. **Environment Variables:** Gevoelige keys staan alleen in `.env`.

## 🛠️ Installatie op een nieuwe LXC
Op je nieuwe Debian LXC kun je het project in één keer installeren met dit commando:
```bash
bash <(curl -sL https://raw.githubusercontent.com/Ivoozz/GeminiNexus/main/install.sh)
```
*(Vervang 'jouw-gebruikersnaam' door je echte GitHub naam na het pushen).*

Of handmatig:
1.  Kloon de repo: `git clone https://github.com/Ivoozz/GeminiNexus.git`
2.  Ga naar de map: `cd GeminiNexus`
3.  Draai de installer: `chmod +x install.sh && ./install.sh`

## ⚙️ Configuratie
1. **Genereer je wachtwoord hash:**
   ```bash
   source venv/bin/activate
   python3 scripts/setup_password.py
   ```
2. Kopieer de output naar je `.env` bestand.
3. Vul je Telegram- en SMTP-gegevens in in `.env`.

## 🚀 Starten
```bash
source venv/bin/activate
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
GeminiNexus is nu bereikbaar op `http://<LXC_IP>:8000`.
