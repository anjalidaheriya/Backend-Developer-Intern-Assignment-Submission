"""Authentication routes"""
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from bson import ObjectId

from models.user import UserCreate, UserLogin, UserResponse, AuthResponse, ForgotPassword, ResetPassword, PasswordChange
from services.user_service import UserService
from middleware.auth import (
    hash_password, verify_password, create_access_token, 
    create_refresh_token, get_jwt_secret, generate_reset_token,
    get_current_user, JWT_ALGORITHM
)
import jwt

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Brute force protection settings
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


@router.post("/register", response_model=AuthResponse)
async def register(user_data: UserCreate, request: Request, response: Response):
    """Register a new user"""
    db = request.app.state.db
    user_service = UserService(db)
    
    # Create user (always as viewer for self-registration)
    user = await user_service.create_user(user_data, created_by_admin=False)
    
    # Generate tokens
    access_token = create_access_token(user.id, user.email, user.role)
    refresh_token = create_refresh_token(user.id)
    
    # Set cookies
    response.set_cookie(
        key="access_token", value=access_token, httponly=True,
        secure=False, samesite="lax", max_age=900, path="/"
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True,
        secure=False, samesite="lax", max_age=604800, path="/"
    )
    
    return AuthResponse(user=user, message="Registration successful")


@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserLogin, request: Request, response: Response):
    """Login user"""
    db = request.app.state.db
    user_service = UserService(db)
    
    email = credentials.email.lower()
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{client_ip}:{email}"
    
    # Check brute force lockout
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt:
        if attempt.get("locked_until") and attempt["locked_until"] > datetime.now(timezone.utc):
            remaining = (attempt["locked_until"] - datetime.now(timezone.utc)).seconds // 60
            raise HTTPException(
                status_code=429, 
                detail=f"Account locked. Try again in {remaining + 1} minutes."
            )
    
    # Get user
    user = await user_service.get_user_by_email(email)
    if not user:
        await _record_failed_attempt(db, identifier)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Check status
    if user.get("status") == "inactive":
        raise HTTPException(status_code=403, detail="Account is inactive")
    
    # Verify password
    if not verify_password(credentials.password, user["password_hash"]):
        await _record_failed_attempt(db, identifier)
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Clear failed attempts on successful login
    await db.login_attempts.delete_one({"identifier": identifier})
    
    # Generate tokens
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, user["email"], user["role"])
    refresh_token = create_refresh_token(user_id)
    
    # Set cookies
    response.set_cookie(
        key="access_token", value=access_token, httponly=True,
        secure=False, samesite="lax", max_age=900, path="/"
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True,
        secure=False, samesite="lax", max_age=604800, path="/"
    )
    
    user_response = UserResponse(
        id=user_id,
        email=user["email"],
        name=user["name"],
        role=user["role"],
        status=user.get("status", "active"),
        created_at=user["created_at"]
    )
    
    return AuthResponse(user=user_response, message="Login successful")


@router.post("/logout")
async def logout(response: Response, user: dict = Depends(get_current_user)):
    """Logout user"""
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current user info"""
    return UserResponse(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        status=user.get("status", "active"),
        created_at=user["created_at"]
    )


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    """Refresh access token"""
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="Refresh token not found")
    
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        db = request.app.state.db
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Generate new access token
        access_token = create_access_token(str(user["_id"]), user["email"], user["role"])
        
        response.set_cookie(
            key="access_token", value=access_token, httponly=True,
            secure=False, samesite="lax", max_age=900, path="/"
        )
        
        return {"message": "Token refreshed"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@router.post("/forgot-password")
async def forgot_password(data: ForgotPassword, request: Request):
    """Request password reset"""
    db = request.app.state.db
    user_service = UserService(db)
    
    user = await user_service.get_user_by_email(data.email)
    # Don't reveal if user exists
    if user:
        token = generate_reset_token()
        await db.password_reset_tokens.insert_one({
            "user_id": str(user["_id"]),
            "token": token,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "used": False,
            "created_at": datetime.now(timezone.utc)
        })
        # In production, send email. For now, log it.
        print(f"Password reset link: /reset-password?token={token}")
    
    return {"message": "If the email exists, a reset link will be sent"}


@router.post("/reset-password")
async def reset_password(data: ResetPassword, request: Request):
    """Reset password with token"""
    db = request.app.state.db
    
    token_doc = await db.password_reset_tokens.find_one({
        "token": data.token,
        "used": False,
        "expires_at": {"$gt": datetime.now(timezone.utc)}
    })
    
    if not token_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Update password
    await db.users.update_one(
        {"_id": ObjectId(token_doc["user_id"])},
        {"$set": {"password_hash": hash_password(data.new_password)}}
    )
    
    # Mark token as used
    await db.password_reset_tokens.update_one(
        {"_id": token_doc["_id"]},
        {"$set": {"used": True}}
    )
    
    return {"message": "Password reset successful"}


@router.post("/change-password")
async def change_password(data: PasswordChange, request: Request, 
                         user: dict = Depends(get_current_user)):
    """Change password for authenticated user"""
    db = request.app.state.db
    user_service = UserService(db)
    
    await user_service.change_password(user["id"], data.current_password, data.new_password)
    return {"message": "Password changed successfully"}


async def _record_failed_attempt(db, identifier: str):
    """Record failed login attempt"""
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    
    if attempt:
        count = attempt.get("count", 0) + 1
        update = {"count": count, "last_attempt": datetime.now(timezone.utc)}
        
        if count >= MAX_LOGIN_ATTEMPTS:
            update["locked_until"] = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
        
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {"$set": update}
        )
    else:
        await db.login_attempts.insert_one({
            "identifier": identifier,
            "count": 1,
            "last_attempt": datetime.now(timezone.utc)
        })
