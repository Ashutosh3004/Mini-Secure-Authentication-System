from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

# Import Rate Limiter tools
from slowapi import Limiter
from slowapi.util import get_remote_address

from database import get_db
from models import User
from schemas import UserCreate, UserResponse, TokenResponse
from security import hash_password, verify_password
from auth import create_access_token, SECRET_KEY, ALGORITHM

import pyotp

# This function checks if the 6-digit code is valid
def verify_totp(secret, code):
    totp = pyotp.TOTP(secret)
    return totp.verify(code)

# Custom key function to bypass OPTIONS (pre-flight) requests
# This prevents the "Server Offline" error during the CORS handshake
def bypass_options_key(request: Request):
    if request.method == "OPTIONS":
        return None  # No limit for OPTIONS
    return get_remote_address(request)

# Initialize the limiter with the custom key function
limiter = Limiter(key_func=bypass_options_key)
router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    try:
        user_exists = db.query(User).filter(User.email == user_in.email).first()
        if user_exists:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        hashed_pwd = hash_password(user_in.password)
        
        # NEW: Automatically generate a 2FA secret for the new user
        # This ensures 2FA triggers during your login test
        generated_secret = pyotp.random_base32() 
        
        new_user = User(
            username=user_in.username,
            email=user_in.email,
            password=hashed_pwd,
            otp_secret=generated_secret  # Save the secret key
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        print(f"DEBUG: User {new_user.email} registered with secret: {generated_secret}")
        return new_user
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error during registration")
    
# Applied limit: 5 login attempts per minute per IP
# The decorator now uses the custom logic to ignore OPTIONS requests
@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # CHECK FOR 2FA: If the user has an otp_secret set in the DB
    if user.otp_secret:
        return {
            "access_token": "pending", 
            "token_type": "bearer", 
            "requires_2fa": True
        }

    # If no 2FA is set up, log in normally
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "requires_2fa": False
    }

# NEW: The endpoint the Frontend calls to verify the 6-digit code
@router.post("/verify-2fa", response_model=TokenResponse)
def verify_2fa(data: dict, db: Session = Depends(get_db)):
    email = data.get("email")
    otp = data.get("otp")
    
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not user.otp_secret or not verify_totp(user.otp_secret, otp):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP code"
        )
        
    # If OTP is correct, issue the final JWT token
    access_token = create_access_token(data={"sub": user.email})
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "requires_2fa": False
    }

@router.get("/profile", response_model=UserResponse)
def get_profile(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user