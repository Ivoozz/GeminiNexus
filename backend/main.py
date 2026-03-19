from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
import logging
import time
import secrets
import traceback
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv, set_key
from .gemini_bridge import ask_gemini
import subprocess

# Load environment variables
ENV_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
load_dotenv(ENV_FILE)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GeminiNexus")

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

# Setup hashing & security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="GeminiNexus AI Assistant")

# Serve static files (frontend)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

class OnboardRequest(BaseModel):
    password: str
    telegram_token: str = ""
    telegram_chat_id: str = ""
    smtp_host: str = ""
    smtp_port: str = ""
    smtp_user: str = ""
    smtp_pass: str = ""
    imap_host: str = ""
    imap_port: str = ""
    imap_user: str = ""
    imap_pass: str = ""

class LoginRequest(BaseModel):
    password: str

class ChatRequest(BaseModel):
    message: str

# Helper functions
def get_password_hash():
    try:
        load_dotenv(ENV_FILE)
        pwd_hash = os.getenv("PASSWORD_HASH")
        if pwd_hash and pwd_hash.startswith("$2b$"):
            return pwd_hash
        return None
    except Exception as e:
        logger.error(f"Fout bij lezen password hash: {str(e)}")
        return None

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = time.time() + (3600 * 24) 
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=403, detail="Sessie verlopen")

@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/api/setup-status")
async def setup_status():
    """Checks if the app has been onboarded."""
    return {"onboarded": get_password_hash() is not None}

@app.post("/api/onboard")
async def onboard(request: OnboardRequest):
    """Initial setup of the application."""
    logger.info("Onboarding gestart...")
    try:
        if get_password_hash():
            raise HTTPException(status_code=400, detail="App is al geconfigureerd.")
        
        # Generate password hash
        logger.info("Wachtwoord hashen...")
        hashed_pwd = pwd_context.hash(request.password)
        
        # Update .env file
        logger.info(f"Gegevens opslaan in {ENV_FILE}...")
        
        if not os.path.exists(ENV_FILE):
            with open(ENV_FILE, "w") as f:
                f.write(f"SECRET_KEY={secrets.token_urlsafe(32)}\n")
        
        # Helper function to set keys safely
        def safe_set_key(key, value):
            if value:
                try:
                    set_key(ENV_FILE, key, str(value))
                except Exception as e:
                    logger.error(f"Fout bij opslaan {key}: {str(e)}")
                    raise e

        safe_set_key("PASSWORD_HASH", hashed_pwd)
        safe_set_key("TELEGRAM_TOKEN", request.telegram_token)
        safe_set_key("TELEGRAM_CHAT_ID", request.telegram_chat_id)
        safe_set_key("SMTP_HOST", request.smtp_host)
        safe_set_key("SMTP_PORT", request.smtp_port)
        safe_set_key("SMTP_USER", request.smtp_user)
        safe_set_key("SMTP_PASS", request.smtp_pass)
        safe_set_key("IMAP_HOST", request.imap_host)
        safe_set_key("IMAP_PORT", request.imap_port)
        safe_set_key("IMAP_USER", request.imap_user)
        safe_set_key("IMAP_PASS", request.imap_pass)
        
        logger.info("Onboarding succesvol afgerond.")
        return {"status": "success"}

    except Exception as e:
        error_detail = traceback.format_exc()
        logger.error(f"CRITICAL ONBOARDING ERROR: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Onboarding fout: {str(e)}")

@app.post("/api/login")
async def login(request: LoginRequest):
    try:
        current_hash = get_password_hash()
        if not current_hash:
            raise HTTPException(status_code=400, detail="Voer eerst de onboarding uit.")
        
        if pwd_context.verify(request.password, current_hash):
            token = create_access_token(data={"sub": "admin"})
            return {"access_token": token, "token_type": "bearer"}
        
        raise HTTPException(status_code=401, detail="Onjuist wachtwoord")
    except Exception as e:
        logger.error(f"Login fout: {str(e)}")
        raise HTTPException(status_code=500, detail="Login mislukt.")

@app.post("/api/chat")
async def chat(request: ChatRequest, user: dict = Depends(get_current_user)):
    try:
        ai_response = ask_gemini(request.message)
        return {"response": ai_response}
    except Exception as e:
        logger.error(f"AI Fout: {str(e)}")
        return {"response": f"Er is een fout opgetreden bij de AI: {str(e)}"}

@app.get("/api/status")
async def system_status(user: dict = Depends(get_current_user)):
    try:
        disk = subprocess.check_output(["df", "-h", "/"]).decode("utf-8").split("\n")[1].split()
        mem = subprocess.check_output(["free", "-m"]).decode("utf-8").split("\n")[1].split()
        return {"status": "online", "disk_usage": disk[4], "memory_usage": f"{mem[2]}MB / {mem[1]}MB"}
    except:
        return {"status": "error"}
