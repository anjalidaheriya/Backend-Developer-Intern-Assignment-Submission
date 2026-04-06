"""User service - business logic for user operations"""
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from fastapi import HTTPException

from models.user import UserCreate, UserUpdate, UserResponse, UserRole, UserStatus
from middleware.auth import hash_password, verify_password


class UserService:
    def __init__(self, db):
        self.db = db
        self.collection = db.users
    
    async def create_user(self, user_data: UserCreate, created_by_admin: bool = False) -> UserResponse:
        """Create a new user"""
        # Normalize email
        email = user_data.email.lower()
        
        # Check if user exists
        existing = await self.collection.find_one({"email": email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create user document
        user_doc = {
            "email": email,
            "password_hash": hash_password(user_data.password),
            "name": user_data.name,
            "role": user_data.role.value if created_by_admin else UserRole.VIEWER.value,
            "status": UserStatus.ACTIVE.value,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None
        }
        
        result = await self.collection.insert_one(user_doc)
        user_doc["id"] = str(result.inserted_id)
        
        return UserResponse(
            id=user_doc["id"],
            email=user_doc["email"],
            name=user_doc["name"],
            role=user_doc["role"],
            status=user_doc["status"],
            created_at=user_doc["created_at"]
        )
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Get user by ID"""
        try:
            user = await self.collection.find_one({"_id": ObjectId(user_id)})
        except Exception:
            return None
        
        if not user:
            return None
        
        return UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            name=user["name"],
            role=user["role"],
            status=user.get("status", UserStatus.ACTIVE.value),
            created_at=user["created_at"],
            updated_at=user.get("updated_at")
        )
    
    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email (includes password hash for auth)"""
        user = await self.collection.find_one({"email": email.lower()})
        if user:
            user["id"] = str(user["_id"])
        return user
    
    async def list_users(self, page: int = 1, page_size: int = 20, 
                         role: Optional[str] = None, status: Optional[str] = None) -> dict:
        """List users with pagination and filtering"""
        query = {}
        if role:
            query["role"] = role
        if status:
            query["status"] = status
        
        # Get total count
        total = await self.collection.count_documents(query)
        
        # Get paginated results
        skip = (page - 1) * page_size
        cursor = self.collection.find(query, {"password_hash": 0}).skip(skip).limit(page_size).sort("created_at", -1)
        users = await cursor.to_list(length=page_size)
        
        user_responses = [
            UserResponse(
                id=str(u["_id"]),
                email=u["email"],
                name=u["name"],
                role=u["role"],
                status=u.get("status", UserStatus.ACTIVE.value),
                created_at=u["created_at"],
                updated_at=u.get("updated_at")
            ) for u in users
        ]
        
        return {
            "users": user_responses,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    
    async def update_user(self, user_id: str, update_data: UserUpdate, 
                          requester_role: str) -> UserResponse:
        """Update user details"""
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Build update document
        update_doc = {"updated_at": datetime.now(timezone.utc)}
        
        if update_data.name is not None:
            update_doc["name"] = update_data.name
        
        # Only admin can change roles
        if update_data.role is not None:
            if requester_role != "admin":
                raise HTTPException(status_code=403, detail="Only admin can change user roles")
            update_doc["role"] = update_data.role.value
        
        # Only admin can change status
        if update_data.status is not None:
            if requester_role != "admin":
                raise HTTPException(status_code=403, detail="Only admin can change user status")
            update_doc["status"] = update_data.status.value
        
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_doc}
        )
        
        return await self.get_user_by_id(user_id)
    
    async def delete_user(self, user_id: str, requester_id: str) -> bool:
        """Delete user (soft delete by setting status to inactive)"""
        if user_id == requester_id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"status": UserStatus.INACTIVE.value, "updated_at": datetime.now(timezone.utc)}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return True
    
    async def change_password(self, user_id: str, current_password: str, 
                              new_password: str) -> bool:
        """Change user password"""
        user = await self.collection.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not verify_password(current_password, user["password_hash"]):
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "password_hash": hash_password(new_password),
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        return True
