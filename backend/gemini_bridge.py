import subprocess
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GeminiBridge")

def ask_gemini(prompt: str) -> str:
    """
    Calls the 'gemini' CLI and filters out internal CLI noise.
    """
    try:
        # We voegen een kleine instructie toe aan de prompt voor schone output
        system_suffix = "\n(Antwoord direct en beknopt, zonder uitleg over je proces of tools.)"
        cmd = ["gemini", prompt + system_suffix]
        
        logger.info(f"Sending prompt to Gemini CLI...")
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        raw_output = result.stdout.strip()
        
        # Opschonen van de output:
        # 1. Verwijder MCP waarschuwingen
        # 2. Verwijder "I will ..." zinnen (de interne planning van de CLI)
        # 3. Verwijder lege regels aan het begin
        
        lines = raw_output.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Filter MCP meldingen
            if "MCP issues detected" in line or "/mcp list" in line:
                continue
            # Filter de "I will search/check/etc" gedachten
            if re.match(r"^(I|i) will\s", line.strip()):
                continue
            # Filter markdown-achtige proces meldingen
            if line.strip().startswith("Thinking...") or line.strip().startswith("Searching..."):
                continue
                
            cleaned_lines.append(line)
            
        final_output = '\n'.join(cleaned_lines).strip()
        
        # Als er na filtering niets overblijft, geef de raw output (voor de zekerheid)
        return final_output if final_output else raw_output
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error calling Gemini CLI: {e.stderr}")
        return f"Fout bij het aanroepen van Gemini CLI: {e.stderr}"
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return f"Er is een onverwachte fout opgetreden: {str(e)}"
