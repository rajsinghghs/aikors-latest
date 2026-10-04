"""
routes/auth.py - Authentication endpoints (signup, login, me, password reset, Google Callback Flow)
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import jwt, JWTError
import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import secrets
import requests

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from database import get_db
import models
import schemas
from auth.password import hash_password, verify_password
from auth.jwt_handler import create_access_token, get_current_user

# Load environment variables
load_dotenv()

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ─── INLINE SCHEMAS ──────────────────────────────────────────────────────────
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
# ─────────────────────────────────────────────────────────────────────────────

# ─── CONFIGURATION (From .env) & DYNAMIC URLS ────────────────────────────────
RESET_SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-for-password-reset")
ALGORITHM = "HS256"

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SENDER_EMAIL = os.getenv("SMTP_EMAIL")       
SENDER_PASSWORD = os.getenv("SMTP_PASSWORD") 

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# DYNAMIC URL GENERATION (Based on single BASE_URL)
# rstrip('/') is used to prevent double slashes
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")

FRONTEND_URL = f"{BASE_URL}/reset-password"
FRONTEND_LOGIN_SUCCESS = f"{BASE_URL}/dashboard"

# 🚀 FIX: Added /api/ before /auth/google/callback so it perfectly matches your backend routing!
GOOGLE_REDIRECT_URI = f"{BASE_URL}/api/auth/google/callback"
# ─────────────────────────────────────────────────────────────────────────────

def generate_slug_from_email(email: str) -> str:
    return email.split("@")[0]

def create_reset_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode = {"exp": expire, "sub": email}
    return jwt.encode(to_encode, RESET_SECRET_KEY, algorithm=ALGORITHM)

def verify_reset_token(token: str) -> str:
    try:
        payload = jwt.decode(token, RESET_SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

def send_reset_email(to_email: str, token: str):
    reset_link = f"{FRONTEND_URL}?token={token}"
    msg = EmailMessage()
    msg.set_content(
        f"Hello,\n\n"
        f"You requested a password reset. Please click the link below to set a new password.\n"
        f"This link is valid for 15 minutes.\n\n"
        f"{reset_link}\n\n"
        f"If you didn't request this, please ignore this email securely."
    )
    msg['Subject'] = 'Aikors - Password Reset Request'
    msg['From'] = SENDER_EMAIL or "system@yourdomain.com"
    msg['To'] = to_email

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")


# ─── GOOGLE AUTH REDIRECT & CALLBACK (SERVER SIDE FLOW) ──────────────────────

@router.get("/google/login")
def google_login():
    """Redirects the user to Google's OAuth 2.0 consent screen."""
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured properly.")
        
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"response_type=code&client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={GOOGLE_REDIRECT_URI}&"
        f"scope=openid%20email%20profile&access_type=offline"
    )
    return RedirectResponse(google_auth_url)


@router.get("/google/callback")
def google_callback(code: str, db: Session = Depends(get_db)):
    """Google redirects here after login. We exchange the code for user info."""
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    
    # Get tokens from Google
    response = requests.post(token_url, data=data)
    if not response.ok:
        raise HTTPException(status_code=400, detail="Failed to exchange authorization code with Google.")
        
    token_data = response.json()
    id_token_jwt = token_data.get("id_token")
    
    if not id_token_jwt:
        raise HTTPException(status_code=400, detail="No ID token received from Google.")

    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            id_token_jwt, 
            google_requests.Request(), 
            GOOGLE_CLIENT_ID
        )
        
        email = idinfo.get("email").lower()
        name = idinfo.get("name")
        picture = idinfo.get("picture") 

        user = db.query(models.User).filter(models.User.email == email).first()
        
        if not user:
            # Register new user
            dummy_password = secrets.token_urlsafe(16) 
            user = models.User(
                name=name,
                email=email,
                hashed_password=hash_password(dummy_password),
                role=models.UserRole.user,
                avatar_url=picture
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            # Existing user login & Avatar update
            if picture and user.avatar_url != picture:
                user.avatar_url = picture
                db.commit()
                db.refresh(user)

        if not user.is_active:
            return RedirectResponse(f"{BASE_URL}/login?error=account_disabled")

        # Create our platform Token
        platform_token = create_access_token({"sub": str(user.id), "role": user.role.value})
        
        # Redirect the user to the frontend dashboard with the token
        return RedirectResponse(f"{FRONTEND_LOGIN_SUCCESS}?token={platform_token}")

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google Token.")


# ─── EXISTING AUTH ROUTES (Signup, Login, Me) ────────────────────────────────

@router.post("/signup", response_model=schemas.Token, status_code=status.HTTP_201_CREATED)
def signup(user_data: schemas.UserSignup, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user_data.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        name=user_data.name,
        email=user_data.email.lower(),
        hashed_password=hash_password(user_data.password),
        role=models.UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return schemas.Token(access_token=token, user=schemas.UserResponse.model_validate(user))


@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email.lower()).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return schemas.Token(access_token=token, user=schemas.UserResponse.model_validate(user))


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=schemas.UserResponse)
def update_me(
    update_data: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if update_data.name:
        current_user.name = update_data.name
    if update_data.avatar_url is not None:
        current_user.avatar_url = update_data.avatar_url
    db.commit()
    db.refresh(current_user)
    return current_user


# ─── PASSWORD RESET ROUTES ───────────────────────────────────────────────────

@router.post("/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == request.email.lower()).first()
    if user:
        token = create_reset_token(user.email)
        background_tasks.add_task(send_reset_email, user.email, token)
    return {"message": "If an account with this email exists, a password reset link has been sent."}


@router.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    email = verify_reset_token(request.token)
    if not email:
        raise HTTPException(status_code=400, detail="Reset link is invalid or has expired.")
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    user.hashed_password = hash_password(request.new_password)
    db.commit()
    return {"message": "Password has been reset successfully. You can now log in."}