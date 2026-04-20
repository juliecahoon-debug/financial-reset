from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserCreate(BaseModel):
    """Schema for creating a new user"""
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None

class UserUpdate(BaseModel):
    """Schema for updating user"""
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    """Schema for returning user data"""
    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
