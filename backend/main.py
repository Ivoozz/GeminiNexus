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
import bcrypt
from jose import jwt
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
SECRET_KEY = os.getenv("SECRET_KEY", "nexus-fallback-key-123")
ALGORITHM = "HS256"

app = FastAPI(title="GeminiNexus OpenAI Gateway")

# Serve static files
frontend_path = os.path.join(BASE_DIR, "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# Models
class OnboardRequest(BaseModel):
    password: str
    telegram_token: str = ""
    telegram_chat_id: str = ""

class ChatCompletionRequest(BaseModel):
    model: str = "gemini-cli"
    messages: list
    stream: bool = True

# Security
security = HTTPBearer()

def get_password_hash():
    load_dotenv(ENV_FILE)
    h = os.getenv("PASSWORD_HASH")
    return h if h and h.startswith("$2b$") else None

def verify_token(token: str):
    try: return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except: return None

async def get_user(creds: HTTPAuthorizationCredentials = Security(security)):
    p = verify_token(creds.credentials)
    if not p: raise HTTPException(status_code=403)
    return p

@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/api/setup-status")
async def setup_status():
    return {"onboarded": get_password_hash() is not None}

@app.post("/api/onboard")
async def onboard(request: OnboardRequest):
    if get_password_hash(): raise HTTPException(status_code=400)
    h = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, "w") as f: f.write(f"SECRET_KEY={secrets.token_urlsafe(32)}\n")
    set_key(ENV_FILE, "PASSWORD_HASH", h)
    for k, v in request.dict().items():
        if k != "password" and v: set_key(ENV_FILE, k.upper(), str(v))
    return {"status": "success"}

@app.post("/api/login")
async def login(request: dict):
    pwd = request.get("password")
    h = get_password_hash()
    if h and bcrypt.checkpw(pwd.encode(), h.encode()):
        return {"access_token": jwt.encode({"sub": "admin", "exp": time.time() + 86400}, SECRET_KEY, algorithm=ALGORITHM)}
    raise HTTPException(status_code=401)

# --- OPENAI COMPATIBLE ENDPOINT ---
@app.post("/v1/chat/completions")
async def chat_completions(request: Request, body: ChatCompletionRequest, user: dict = Depends(get_user)):
    # Extract last message
    last_msg = body.messages[-1]["content"]
    
    async def event_generator():
        # Force YOLO mode in the bridge call via the system instruction already in gemini_bridge.py
        for chunk in stream_gemini(last_msg):
            if await request.is_disconnected(): break
            # OpenAI format wrapper
            yield json.dumps({
                "id": "nexus-" + secrets.token_hex(4),
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": body.model,
                "choices": [{"delta": {"content": chunk}, "index": 0, "finish_reason": None}]
            })

    return EventSourceResponse(event_generator())

@app.get("/api/status")
async def system_status(user: dict = Depends(get_user)):
    try:
        disk = subprocess.check_output(["df", "-h", "/"]).decode().split("\n")[1].split()[4]
        mem = subprocess.check_output(["free", "-m"]).decode().split("\n")[1].split()
        return {"disk": disk, "mem": f"{mem[2]}MB", "uptime": subprocess.check_output(["uptime", "-p"]).decode().strip()}
    except: return {"status": "error"}

@app.get("/api/files")
async def list_files(user: dict = Depends(get_user)):
    return [{"name": f, "size": os.path.getsize(os.path.join(DATA_DIR, f))} for f in os.listdir(DATA_DIR)]

@app.get("/api/logs")
async def get_logs(user: dict = Depends(get_user)):
    try:
        logs = subprocess.check_output(["journalctl", "-u", "gemininexus", "-n", "100", "--no-pager"]).decode()
        return {"logs": logs}
    except: return {"logs": "Logs unavailable."}
