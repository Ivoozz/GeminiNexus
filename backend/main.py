from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
import logging
import time
import secrets
import json
import traceback
import bcrypt
from jose import JWTError, jwt
from dotenv import load_dotenv, set_key
from .gemini_bridge import stream_gemini
import subprocess
from sse_starlette.sse import EventSourceResponse

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_FILE = os.path.join(BASE_DIR, ".env")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

load_dotenv(ENV_FILE)

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("GeminiNexus")

app = FastAPI(title="GeminiNexus AI Assistant")

# Serve static files
frontend_path = os.path.join(BASE_DIR, "frontend")
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

# Security Helpers
security = HTTPBearer()

def get_password_hash():
    load_dotenv(ENV_FILE)
    pwd_hash = os.getenv("PASSWORD_HASH")
    return pwd_hash if pwd_hash and pwd_hash.startswith("$2b$") else None

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
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
        raise HTTPException(status_code=400, detail="Al geconfigureerd")
    
    hashed_pwd = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()
    
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, "w") as f:
            f.write(f"SECRET_KEY={secrets.token_urlsafe(32)}\n")
    
    set_key(ENV_FILE, "PASSWORD_HASH", hashed_pwd)
    # Save other keys...
    fields = request.dict()
    for key, val in fields.items():
        if key != "password" and val:
            set_key(ENV_FILE, key.upper(), str(val))
            
    return {"status": "success"}

@app.post("/api/login")
async def login(request: dict):
    pwd = request.get("password")
    current_hash = get_password_hash()
    if current_hash and bcrypt.checkpw(pwd.encode(), current_hash.encode()):
        token = jwt.encode({"sub": "admin", "exp": time.time() + 86400}, SECRET_KEY, algorithm=ALGORITHM)
        return {"access_token": token}
    raise HTTPException(status_code=401)

@app.get("/api/chat/stream")
async def chat_stream(request: Request, message: str, token: str):
    if not verify_token(token): raise HTTPException(status_code=403)
    async def gen():
        for line in stream_gemini(message):
            if await request.is_disconnected(): break
            yield {"data": line}
    return EventSourceResponse(gen())

@app.get("/api/status")
async def system_status(user: dict = Depends(get_current_user)):
    try:
        disk = subprocess.check_output(["df", "-h", "/"]).decode().split("\n")[1].split()[4]
        mem = subprocess.check_output(["free", "-m"]).decode().split("\n")[1].split()
        return {"disk": disk, "mem": f"{mem[2]}MB / {mem[1]}MB", "uptime": subprocess.check_output(["uptime", "-p"]).decode().strip()}
    except: return {"status": "error"}

# NEW: File Explorer API
@app.get("/api/files")
async def list_files(user: dict = Depends(get_current_user)):
    files = []
    for f in os.listdir(DATA_DIR):
        path = os.path.join(DATA_DIR, f)
        files.append({"name": f, "size": os.path.getsize(path), "mtime": os.path.getmtime(path)})
    return files

# NEW: Log Viewer API
@app.get("/api/logs")
async def get_logs(user: dict = Depends(get_current_user)):
    try:
        logs = subprocess.check_output(["journalctl", "-u", "gemininexus", "-n", "50", "--no-pager"]).decode()
        return {"logs": logs}
    except: return {"logs": "Kon logs niet ophalen."}
