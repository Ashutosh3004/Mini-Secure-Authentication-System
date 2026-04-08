import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt

# In a production environment, these should be loaded from environment variables
# Example: SECRET_KEY = os.getenv("SECRET_KEY")
SECRET_KEY = os.getenv("SECRET_KEY", "fallback_dev_key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Generates a signed JSON Web Token (JWT) with an expiration timestamp.
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Add the expiration ('exp') claim to the payload
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt