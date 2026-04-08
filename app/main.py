from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import routes
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# 1. Initialize the Limiter Tracking by IP
limiter = Limiter(key_func=get_remote_address)

# 2. Define the APP Instance
app = FastAPI(title="Mini Secure Authentication Server")

# 3. SET UP CORS FIRST (The "Permission Slip")
# This MUST be the first middleware added so it can handle pre-flight OPTIONS requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows your Live Server (port 5500) to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Attach Limiter State and Error Handler
# We attach this to the app state so routes.py can access it
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 5. Physical Database Integration
# Create database tables on startup if they don't exist
Base.metadata.create_all(bind=engine)

# 6. Include the Router (The Logic Tier)
# This brings in your Register, Login, and 2FA routes
app.include_router(routes.router)

@app.get("/")
def root():
    return {
        "status": "Secure Auth Backend Running",
        "info": "Multi-Factor Authentication & Rate Limiting Active"
    }