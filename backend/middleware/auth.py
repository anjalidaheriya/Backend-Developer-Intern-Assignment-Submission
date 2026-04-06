"""Authentication and authorization middleware"""
import os
import jwt
import bcrypt
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable
from functools import wraps
from fastapi import Request, HTTPException, Depends
from bson import ObjectId

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def get_jwt_secret() -> str:
    """Get JWT secret from environment"""
    return os.environ.get("JWT_SECRET", "default-secret-change-in-production")


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: str, email: str, role: str) -> str:
    """Create JWT access token"""
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access"
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create JWT refresh token"""
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh"
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def generate_reset_token() -> str:
    """Generate password reset token"""
    return secrets.token_urlsafe(32)


async def get_current_user(request: Request) -> dict:
    """Extract and validate current user from JWT token"""
    # Try cookie first, then Authorization header
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        # Get db from app state
        db = request.app.state.db
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if user.get("status") == "inactive":
            raise HTTPException(status_code=403, detail="User account is inactive")
        
        # Return user data without sensitive fields
        return {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "status": user.get("status", "active"),
            "created_at": user["created_at"]
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_roles(*allowed_roles: str):
    """Decorator to require specific roles for an endpoint"""
    async def role_checker(request: Request) -> dict:
        user = await get_current_user(request)
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return user
    return role_checker


# Role-based dependency functions
async def require_admin(request: Request) -> dict:
    """Require admin role"""
    user = await get_current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_analyst_or_admin(request: Request) -> dict:
    """Require analyst or admin role"""
    user = await get_current_user(request)
    if user["role"] not in ["analyst", "admin"]:
        raise HTTPException(status_code=403, detail="Analyst or Admin access required")
    return user


async def require_any_authenticated(request: Request) -> dict:
    """Require any authenticated user"""
    return await get_current_user(request)
