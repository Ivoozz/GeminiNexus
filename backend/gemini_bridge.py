import subprocess
import shlex
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GeminiBridge")

def ask_gemini(prompt: str) -> str:
    """
    Calls the 'gemini' CLI tool with the given prompt and returns the output.
    Uses the existing authenticated CLI session.
    """
    try:
        # Prepare the command. We use shlex for safe shell splitting.
        cmd = ["gemini", prompt]
        
        logger.info(f"Sending prompt to Gemini CLI: {prompt[:50]}...")
        
        # Run the command and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stderr:
            logger.warning(f"Gemini CLI stderr: {result.stderr}")
            
        return result.stdout.strip()
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error calling Gemini CLI: {e.stderr}")
        return f"Fout bij het aanroepen van Gemini CLI: {e.stderr}"
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return f"Er is een onverwachte fout opgetreden: {str(e)}"

if __name__ == "__main__":
    # Test call
    response = ask_gemini("Hallo, wie ben je?")
    print(f"Gemini antwoordt: {response}")
