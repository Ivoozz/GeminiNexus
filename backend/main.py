from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
import logging
import time
import secrets
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv, set_key
from .gemini_bridge import ask_gemini
import subprocess

# Load environment variables
ENV_FILE = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(ENV_FILE)

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

# Setup hashing & security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GeminiNexus")

app = FastAPI(title="GeminiNexus AI Assistant")

# Serve static files (frontend)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

class OnboardRequest(BaseModel):
    password: str
    telegram_token: str = ""
    telegram_chat_id: str = ""

class LoginRequest(BaseModel):
    password: str

class ChatRequest(BaseModel):
    message: str

# Helper functions
def get_password_hash():
    load_dotenv(ENV_FILE)
    return os.getenv("PASSWORD_HASH")

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
    """Checks if the app has been onboarded (password set)."""
    return {"onboarded": get_password_hash() is not None}

@app.post("/api/onboard")
async def onboard(request: OnboardRequest):
    """Initial setup of the application."""
    if get_password_hash():
        raise HTTPException(status_code=400, detail="App is al geconfigureerd.")
    
    # Generate password hash
    hashed_pwd = pwd_context.hash(request.password)
    
    # Update .env file
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, "w") as f:
            f.write(f"SECRET_KEY={secrets.token_urlsafe(32)}\n")
    
    set_key(ENV_FILE, "PASSWORD_HASH", hashed_pwd)
    if request.telegram_token:
        set_key(ENV_FILE, "TELEGRAM_TOKEN", request.telegram_token)
    if request.telegram_chat_id:
        set_key(ENV_FILE, "TELEGRAM_CHAT_ID", request.telegram_chat_id)
    
    return {"status": "success", "message": "Onboarding voltooid. Herstart de service of log in."}

@app.post("/api/login")
async def login(request: LoginRequest):
    current_hash = get_password_hash()
    if not current_hash:
        raise HTTPException(status_code=400, detail="Voer eerst de onboarding uit.")
    
    if pwd_context.verify(request.password, current_hash):
        token = create_access_token(data={"sub": "admin"})
        return {"access_token": token, "token_type": "bearer"}
    
    raise HTTPException(status_code=401, detail="Onjuist wachtwoord")

@app.post("/api/chat")
async def chat(request: ChatRequest, user: dict = Depends(get_current_user)):
    ai_response = ask_gemini(request.message)
    return {"response": ai_response}

@app.get("/api/status")
async def system_status(user: dict = Depends(get_current_user)):
    try:
        disk = subprocess.check_output(["df", "-h", "/"]).decode("utf-8").split("\n")[1].split()
        mem = subprocess.check_output(["free", "-m"]).decode("utf-8").split("\n")[1].split()
        return {"status": "online", "disk_usage": disk[4], "memory_usage": f"{mem[2]}MB / {mem[1]}MB"}
    except:
        return {"status": "error"}
