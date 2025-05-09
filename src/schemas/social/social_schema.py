from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime

class ShareAchievementRequest(BaseModel):
    """Schema for sharing an achievement"""
    achievement_type: str = Field(..., description="Type of achievement")
    achievement_data: Dict[str, Any] = Field(..., description="Achievement data")

class ShareMealRequest(BaseModel):
    """Schema for sharing a meal"""
    meal_id: str = Field(..., description="Meal ID")
    meal_data: Dict[str, Any] = Field(..., description="Meal data")

class ShareProgressRequest(BaseModel):
    """Schema for sharing progress"""
    progress_type: str = Field(..., description="Type of progress")
    progress_data: Dict[str, Any] = Field(..., description="Progress data")

class Comment(BaseModel):
    """Schema for a comment"""
    id: str
    user_id: str
    user_name: str
    content: str
    created_at: datetime

class SharedPost(BaseModel):
    """Schema for a shared post"""
    id: str
    user_id: str
    user_name: str
    share_type: str
    content: Dict[str, Any]
    privacy: str
    created_at: datetime
    likes: int
    comments: List[Comment]

    class Config:
        orm_mode = True 