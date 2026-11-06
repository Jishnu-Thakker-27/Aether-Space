import os
import sys
import threading
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

# Local modules
import database
import ai_service

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(BASE_DIR, "dist")

# Lifespan event to initialize the database on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[FastAPI Startup] Initializing database and tables...")
    database.init_db()
    yield
    print("[FastAPI Shutdown] Server shutting down.")

# Initialize FastAPI application
app = FastAPI(
    title="Aether Space API",
    description="High-performance conversational AI companion backend powered by FastAPI, Vite, Google Gemini API, and Dual-engine Database (MySQL/SQLite).",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for Vite dev server (http://localhost:5173), production URLs, and local origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Pydantic Schemas
# =============================================================================

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=1)
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=4)

class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)

class GoogleAuthRequest(BaseModel):
    name: Optional[str] = "Google User"
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=4)

class PhoneAuthRequest(BaseModel):
    phone: str = Field(..., min_length=6)
    name: Optional[str] = None
    password: str = Field(..., min_length=4)

class ResetPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3)
    new_password: str = Field(..., min_length=4)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    username: Optional[str] = "Friend"
    email: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None

# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/api/health")
def api_health():
    """Health check endpoint displaying active database engine and API status."""
    return {
        "status": "online",
        "framework": "FastAPI + Vite",
        "message": "Aether Space Chatbot Backend (FastAPI) is running smoothly!",
        "database": "MySQL" if database.MYSQL_ACTIVE else "SQLite",
        "docs": "/docs"
    }

@app.post("/api/register")
def register_user(req: RegisterRequest):
    """Registers a new user with compulsory password."""
    username = req.username.strip()
    email = req.email.strip().lower()
    password = req.password.strip()

    if not username or not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username, email, and password are required."
        )

    if len(password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 4 characters long."
        )

    user_data, error = database.create_user(username, email, password)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {
        "success": True,
        "message": "Registration successful! Welcome to Aether Space.",
        "user": user_data
    }

@app.post("/api/login")
def login_user(req: LoginRequest):
    """Authenticates an existing user and upgrades legacy dummy OAuth hashes automatically."""
    email = req.email.strip().lower()
    password = req.password.strip()

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required."
        )

    user_data, error = database.authenticate_user(email, password)
    if error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error)

    return {
        "success": True,
        "message": "Login successful!",
        "user": user_data
    }

@app.post("/api/google-auth")
def google_auth(req: GoogleAuthRequest):
    """Registers or logs in a user via Google account with compulsory password."""
    name = (req.name or "Google User").strip()
    email = req.email.strip().lower()
    password = req.password.strip()

    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google email is required.")
    if not password or len(password) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required (minimum 4 characters).")

    user_data, error = database.create_or_get_oauth_user(name, email, password)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {
        "success": True,
        "message": "Google sign-in successful!",
        "user": user_data
    }

@app.post("/api/phone-auth")
def phone_auth(req: PhoneAuthRequest):
    """Registers or logs in a user via phone number with compulsory password."""
    phone = req.phone.strip()
    name = (req.name or f"User {phone[-4:] if len(phone)>=4 else 'Phone'}").strip()
    password = req.password.strip()

    if not phone or len(phone) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Valid phone number is required.")
    if not password or len(password) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required (minimum 4 characters).")

    clean_phone = phone.replace(" ", "").replace("+", "").replace("-", "")
    phone_email = f"phone_{clean_phone}@mobile.user"

    user_data, error = database.create_or_get_oauth_user(name, phone_email, password)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {
        "success": True,
        "message": "Phone sign-in successful!",
        "user": user_data
    }

@app.post("/api/reset-password")
def reset_password(req: ResetPasswordRequest):
    """Resets user password."""
    email = req.email.strip().lower()
    new_password = req.new_password.strip()

    if not email or not new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and new password are required.")
    if len(new_password) < 4:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be at least 4 characters long.")

    success, error = database.reset_user_password(email, new_password)
    if error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error)

    return {
        "success": True,
        "message": "Password reset successfully! Please sign in with your new password."
    }

@app.post("/api/chat")
def chat_with_ai(req: ChatRequest):
    """
    High-speed AI chat endpoint:
    - Saves user message asynchronously
    - Queries ultra-fast Gemini 3.1 Flash Lite model (or instant fast-path for greetings)
    - Saves assistant reply asynchronously
    - Returns reply formatted in clean markdown without awkward personalizations
    """
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty.")

    username = (req.username or "Friend").strip()
    email = req.email.strip().lower() if req.email else None

    user_id = None
    if email:
        user_info = database.get_user_by_email(email)
        if user_info:
            user_id = user_info["id"]

    # 1. Asynchronously save user message to database
    threading.Thread(
        target=database.save_chat_message,
        args=(user_id, "user", message),
        daemon=True
    ).start()

    # 2. Convert history to dictionary list format
    history_dicts = []
    if req.history and isinstance(req.history, list):
        for h in req.history:
            if isinstance(h, dict) and "role" in h and "content" in h:
                history_dicts.append({"role": h["role"], "content": h["content"]})

    # 3. Call AI service
    reply_text, source = ai_service.get_ai_response(
        message=message,
        display_name=username,
        history=history_dicts
    )

    # 4. Asynchronously save AI reply to database
    threading.Thread(
        target=database.save_chat_message,
        args=(user_id, "assistant", reply_text),
        daemon=True
    ).start()

    return {"reply": reply_text, "source": source}

@app.get("/api/history")
def get_history(email: Optional[str] = None, limit: int = Query(30, ge=1, le=100)):
    """Retrieves recent conversation history."""
    user_id = None
    if email:
        user_info = database.get_user_by_email(email.strip().lower())
        if user_info:
            user_id = user_info["id"]

    rows = database.get_chat_history(user_id=user_id, limit=limit)
    formatted = [
        {
            "id": r["id"],
            "role": r["role"],
            "message": r["message"],
            "created_at": str(r["created_at"]),
        }
        for r in rows
    ]
    return {"history": formatted}

@app.delete("/api/history")
def clear_history(email: Optional[str] = None):
    """Clears conversation history for the given user."""
    user_id = None
    if email:
        user_info = database.get_user_by_email(email.strip().lower())
        if user_info:
            user_id = user_info["id"]

    success = database.clear_chat_history(user_id=user_id)
    return {"success": success, "message": "Chat history cleared successfully"}

# =============================================================================
# Frontend Static Asset Serving (Vite dist / Local fallback)
# =============================================================================

# Mount Vite production dist assets directory if it exists
if os.path.isdir(os.path.join(DIST_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST_DIR, "assets")), name="dist-assets")

@app.get("/")
def serve_index():
    """Serves the primary UI (either from Vite dist/ or root index.html)."""
    dist_index = os.path.join(DIST_DIR, "index.html")
    if os.path.isfile(dist_index):
        return FileResponse(dist_index)
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/style.css")
def serve_css():
    """Fallback static CSS serving."""
    return FileResponse(os.path.join(BASE_DIR, "style.css"), media_type="text/css")

@app.get("/app.js")
def serve_js():
    """Fallback static JS serving."""
    return FileResponse(os.path.join(BASE_DIR, "app.js"), media_type="application/javascript")

# =============================================================================
# Direct Runner (python main.py [port])
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else int(os.getenv("PORT", 8000))
    print(f"\n🚀 Aether Space FastAPI Server running at: http://127.0.0.1:{port}")
    print(f"📖 Interactive OpenAPI documentation:    http://127.0.0.1:{port}/docs")
    print(f"⚡ Vite Dev Server proxy target:         http://127.0.0.1:{port}/api\n")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)

