import subprocess
import logging
import os
import select
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GeminiBridge")

def stream_gemini(prompt: str):
    """
    Calls the 'gemini' CLI in autonomous mode and yields its output line-by-line.
    """
    # We voegen een krachtig systeem-prompt toe om autonoom gedrag af te dwingen.
    # Ook vertellen we de CLI dat hij 'YOLO' (You Only Live Once) mag gaan.
    system_instruction = (
        "\n[SYSTEEM INSTRUCTIE: Werk VOLLEDIG AUTONOOM. "
        "Voer alle benodigde tools en wijzigingen DIRECT uit zonder om bevestiging te vragen. "
        "Toon je gedachten, tool-aanroepen en resultaten stap voor stap.]\n"
    )
    
    # Commando met autonomous mode (indien ondersteund) of krachtige instructies
    cmd = ["gemini", prompt + system_instruction]
    
    logger.info(f"Starting streaming Gemini session in autonomous mode...")
    
    try:
        # Start de CLI als een subprocess
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, # Vang ook errors op in de stream
            text=True,
            bufsize=1, # Line buffering
            universal_newlines=True
        )

        # Lees de output line-by-line zolang het proces draait
        for line in iter(process.stdout.readline, ""):
            if line:
                yield line
                
        process.stdout.close()
        return_code = process.wait()
        
        if return_code != 0:
            yield f"\n[Systeem: Proces beëindigd met exit code {return_code}]"
            
    except Exception as e:
        logger.error(f"Streaming error: {str(e)}")
        yield f"\n[Fout bij streamen: {str(e)}]"
