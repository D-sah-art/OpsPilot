import time
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from services.common.db import db
from services.common.security import verify_password, create_access_token, decode_token
from telemetry.logger import get_logger
from chaos.engine import chaos_engine

logger = get_logger("auth-service")

app = FastAPI(title="ShopFlow Auth Service", version="1.0.0")

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

@app.get("/health")
def health():
    return {"status": "healthy", "service": "auth-service", "dependencies": {"postgresql": "healthy"}}

@app.get("/auth/users", response_model=List[UserResponse])
def get_demo_users():
    return [
        UserResponse(
            id=u["id"],
            email=u["email"],
            full_name=u["full_name"],
            role=u["role"]
        )
        for u in db.users.values()
    ]

@app.post("/auth/login", response_model=LoginResponse)
def login(request: LoginRequest):
    start = time.time()
    logger.info("AUTH_LOGIN_ATTEMPT", f"Login attempt for user: {request.email}", metadata={"email": request.email})
    
    user = db.get_user_by_email(request.email)
    if not user or not verify_password(request.password, user["password_hash"]):
        latency = (time.time() - start) * 1000
        logger.warn("AUTH_FAILED", f"Invalid credentials for {request.email}", latency_ms=latency, status_code=401)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(data={"sub": user["email"], "user_id": user["id"], "role": user["role"]})
    latency = (time.time() - start) * 1000
    logger.info("AUTH_SUCCESS", f"User {request.email} authenticated successfully", latency_ms=latency, status_code=200)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse(
            id=user["id"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"]
        )
    )

@app.get("/auth/verify", response_model=UserResponse)
def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token")
    
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Token expired or invalid")
    
    user = db.get_user_by_email(payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        role=user["role"]
    )
