"""User management routes"""
from typing import Optional
from fastapi import APIRouter, Request, Depends, Query

from models.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from services.user_service import UserService
from middleware.auth import require_admin, get_current_user

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("", response_model=UserListResponse)
async def list_users(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(require_admin)
):
    """List all users (Admin only)"""
    db = request.app.state.db
    user_service = UserService(db)
    
    result = await user_service.list_users(page, page_size, role, status)
    return UserListResponse(**result)


@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    request: Request,
    admin: dict = Depends(require_admin)
):
    """Create a new user with specific role (Admin only)"""
    db = request.app.state.db
    user_service = UserService(db)
    
    return await user_service.create_user(user_data, created_by_admin=True)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    request: Request,
    user: dict = Depends(require_admin)
):
    """Get user by ID (Admin only)"""
    db = request.app.state.db
    user_service = UserService(db)
    
    result = await user_service.get_user_by_id(user_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    
    return result


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    request: Request,
    user: dict = Depends(get_current_user)
):
    """Update user (Admin can update any, users can only update own name)"""
    db = request.app.state.db
    user_service = UserService(db)
    
    # Non-admin can only update their own profile
    if user["role"] != "admin" and user_id != user["id"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Can only update your own profile")
    
    return await user_service.update_user(user_id, update_data, user["role"])


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    request: Request,
    user: dict = Depends(require_admin)
):
    """Delete (deactivate) user (Admin only)"""
    db = request.app.state.db
    user_service = UserService(db)
    
    await user_service.delete_user(user_id, user["id"])
    return {"message": "User deactivated successfully"}
