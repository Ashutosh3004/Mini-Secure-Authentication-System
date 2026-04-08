from pydantic import BaseModel, EmailStr

# 1. Used for registration input
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

# 2. Used for login input
class UserLogin(BaseModel):
    email: EmailStr
    password: str

# 3. Used for the response when showing user data
class UserResponse(BaseModel):
    id: int
    username: str
    email: str

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    requires_2fa: bool = False # Add this line