from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    name: str

class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str

class UserResponse(UserBase):
    """Schema for user response - used when returning user data"""
    id: str
    created_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True