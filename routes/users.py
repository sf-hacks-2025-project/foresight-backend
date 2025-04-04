from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()

# Example Pydantic models
class User(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None

@router.get("/users", response_model=List[User])
async def get_users():
    """Get all users"""
    # Implement your database query here
    # For now, return dummy data
    return [
        {"id": 1, "username": "user1", "email": "user1@example.com", "is_active": True},
        {"id": 2, "username": "user2", "email": "user2@example.com", "is_active": False}
    ]

@router.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """Get user by ID"""
    # Implement your database query here
    # For now, return dummy data
    return {"id": user_id, "username": f"user{user_id}", "email": f"user{user_id}@example.com", "is_active": True}

@router.put("/users/{user_id}", response_model=User)
async def update_user(user_id: int, user_data: UserUpdate):
    """Update user information"""
    # Implement your database update logic here
    return {
        "id": user_id,
        "username": user_data.username or f"user{user_id}",
        "email": user_data.email or f"user{user_id}@example.com",
        "is_active": True
    }

@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int):
    """Delete a user"""
    # Implement your database delete logic here
    return None 