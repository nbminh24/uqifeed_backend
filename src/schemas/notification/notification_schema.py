from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime
from src.config.database import PyObjectId
from bson import ObjectId

class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class NotificationBase(BaseModel):
    """Base schema for notifications"""
    title: str
    message: str
    type: str  # meal_reminder, weekly_report, nutrition_tip, etc.
    is_read: bool = False
    data: Optional[Dict] = None

class NotificationCreate(NotificationBase):
    """Schema for creating a new notification"""
    user_id: str

class NotificationUpdate(BaseModel):
    """Schema for updating a notification - all fields optional"""
    title: Optional[str] = None
    message: Optional[str] = None
    is_read: Optional[bool] = None
    data: Optional[Dict] = None

class NotificationResponse(NotificationBase, MongoBaseModel):
    """Schema for notification response"""
    user_id: str
    created_at: Optional[datetime] = None
    
class ReminderTimes(BaseModel):
    """Schema for reminder times"""
    breakfast: str = "08:00"  # HH:MM format
    lunch: str = "12:00"
    dinner: str = "18:00"

class NotificationSettingsBase(BaseModel):
    """Base schema for notification settings"""
    meal_reminders: bool = True
    weekly_report: bool = True
    nutrition_tips: bool = True
    progress_updates: bool = True
    marketing: bool = False
    reminder_times: ReminderTimes = Field(default_factory=ReminderTimes)

class NotificationSettingsCreate(NotificationSettingsBase):
    """Schema for creating new notification settings"""
    user_id: str

class NotificationSettingsUpdate(BaseModel):
    """Schema for updating notification settings - all fields optional"""
    meal_reminders: Optional[bool] = None
    weekly_report: Optional[bool] = None
    nutrition_tips: Optional[bool] = None
    progress_updates: Optional[bool] = None
    marketing: Optional[bool] = None
    reminder_times: Optional[ReminderTimes] = None

class NotificationSettingsResponse(NotificationSettingsBase, MongoBaseModel):
    """Schema for notification settings response"""
    user_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None