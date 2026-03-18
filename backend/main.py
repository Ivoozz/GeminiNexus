from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
import logging
import time
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv
from .gemini_bridge import ask_gemini
import subprocess

# Load environment variables
load_dotenv()

# Configuration (Strict security)
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
PASSWORD_HASH = os.getenv("PASSWORD_HASH")

if not SECRET_KEY or not PASSWORD_HASH:
    print("❌ CRITICAL ERROR: SECRET_KEY or PASSWORD_HASH is missing in .env")
    print("Run the install.sh script to configure security correctly.")

# Setup hashing & security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GeminiNexus")

app = FastAPI(title="GeminiNexus AI Assistant")

# Serve static files (frontend)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

class LoginRequest(BaseModel):
    password: str

class ChatRequest(BaseModel):
    message: str

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = time.time() + (3600 * 24) # Valid for 24 hours
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=403, detail="Ongeldig of verlopen token")

@app.get("/")
async def root():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.post("/api/login")
async def login(request: LoginRequest):
    if not PASSWORD_HASH:
        raise HTTPException(status_code=500, detail="Server niet correct geconfigureerd.")
    
    if verify_password(request.password, PASSWORD_HASH):
        token = create_access_token(data={"sub": "admin"})
        return {"access_token": token, "token_type": "bearer"}
    
    raise HTTPException(status_code=401, detail="Onjuist wachtwoord")

@app.post("/api/chat")
async def chat(request: ChatRequest, user: dict = Depends(get_current_user)):
    logger.info(f"Chat request: {request.message[:50]}...")
    ai_response = ask_gemini(request.message)
    return {"response": ai_response}

@app.get("/api/status")
async def system_status(user: dict = Depends(get_current_user)):
    try:
        disk = subprocess.check_output(["df", "-h", "/"]).decode("utf-8").split("\n")[1].split()
        disk_usage = disk[4]
        mem = subprocess.check_output(["free", "-m"]).decode("utf-8").split("\n")[1].split()
        mem_usage = f"{mem[2]}MB / {mem[1]}MB"
        return {"status": "online", "disk_usage": disk_usage, "memory_usage": mem_usage}
    except Exception as e:
        return {"status": "error", "message": str(e)}
