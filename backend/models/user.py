"""User models and schemas"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    VIEWER = "viewer"      # Can only view dashboard data
    ANALYST = "analyst"    # Can view records and access insights
    ADMIN = "admin"        # Full management access


class UserStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


# Request schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=2, max_length=100)
    role: UserRole = UserRole.VIEWER


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str
    new_password: str = Field(..., min_length=6)


# Response schemas
class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    
    id: str
    email: str
    name: str
    role: UserRole
    status: UserStatus = UserStatus.ACTIVE
    created_at: datetime
    updated_at: Optional[datetime] = None


class UserListResponse(BaseModel):
    users: list[UserResponse]
    total: int
    page: int
    page_size: int


class AuthResponse(BaseModel):
    user: UserResponse
    message: str = "Success"
