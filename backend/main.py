from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
import logging
import time
import secrets
import json
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv, set_key
from .gemini_bridge import stream_gemini
import subprocess
from sse_starlette.sse import EventSourceResponse

# Load environment variables
ENV_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
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
    load_dotenv(ENV_FILE)
    pwd_hash = os.getenv("PASSWORD_HASH")
    if pwd_hash and pwd_hash.startswith("$2b$"):
        return pwd_hash
    return None

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = time.time() + (3600 * 24) 
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    payload = verify_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=403, detail="Sessie verlopen")
    return payload

@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/api/setup-status")
async def setup_status():
    return {"onboarded": get_password_hash() is not None}

@app.post("/api/onboard")
async def onboard(request: OnboardRequest):
    if get_password_hash():
        raise HTTPException(status_code=400, detail="App is al geconfigureerd.")
    
    hashed_pwd = pwd_context.hash(request.password)
    
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, "w") as f:
            f.write(f"SECRET_KEY={secrets.token_urlsafe(32)}\n")
    
    set_key(ENV_FILE, "PASSWORD_HASH", hashed_pwd)
    
    # Optional fields
    if request.telegram_token: set_key(ENV_FILE, "TELEGRAM_TOKEN", request.telegram_token)
    if request.telegram_chat_id: set_key(ENV_FILE, "TELEGRAM_CHAT_ID", request.telegram_chat_id)
    if request.smtp_host: set_key(ENV_FILE, "SMTP_HOST", request.smtp_host)
    if request.smtp_port: set_key(ENV_FILE, "SMTP_PORT", request.smtp_port)
    if request.smtp_user: set_key(ENV_FILE, "SMTP_USER", request.smtp_user)
    if request.smtp_pass: set_key(ENV_FILE, "SMTP_PASS", request.smtp_pass)
    if request.imap_host: set_key(ENV_FILE, "IMAP_HOST", request.imap_host)
    if request.imap_port: set_key(ENV_FILE, "IMAP_PORT", request.imap_port)
    if request.imap_user: set_key(ENV_FILE, "IMAP_USER", request.imap_user)
    if request.imap_pass: set_key(ENV_FILE, "IMAP_PASS", request.imap_pass)
    
    return {"status": "success"}

@app.post("/api/login")
async def login(request: LoginRequest):
    current_hash = get_password_hash()
    if not current_hash or not pwd_context.verify(request.password, current_hash):
        raise HTTPException(status_code=401, detail="Onjuist wachtwoord")
    
    token = create_access_token(data={"sub": "admin"})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/api/chat/stream")
async def chat_stream(request: Request, message: str, token: str):
    """
    Streaming endpoint using SSE.
    """
    if not verify_token(token):
        raise HTTPException(status_code=403, detail="Ongeldig token")

    async def event_generator():
        for line in stream_gemini(message):
            # Check if client is still connected
            if await request.is_disconnected():
                logger.info("Client disconnected from stream.")
                break
            
            # Yield data in SSE format
            yield {"data": line}

    return EventSourceResponse(event_generator())

@app.get("/api/status")
async def system_status(user: dict = Depends(get_current_user)):
    try:
        disk = subprocess.check_output(["df", "-h", "/"]).decode("utf-8").split("\n")[1].split()
        mem = subprocess.check_output(["free", "-m"]).decode("utf-8").split("\n")[1].split()
        return {"status": "online", "disk_usage": disk[4], "memory_usage": f"{mem[2]}MB / {mem[1]}MB"}
    except:
        return {"status": "error"}
