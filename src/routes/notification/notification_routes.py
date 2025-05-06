from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict
from datetime import datetime, date, time, timedelta
from bson import ObjectId

from src.config.database import notifications_collection, notification_settings_collection
from src.schemas.notification.notification_schema import (
    NotificationResponse, 
    NotificationSettingsResponse, 
    NotificationSettingsUpdate
)
from src.services.authentication.user_auth import get_current_user

# Initialize router
router = APIRouter(
    tags=["notifications"]
)

# Enhanced notification routes
@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    limit: int = 20,
    offset: int = 0,
    is_read: Optional[bool] = None,
    type: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Get user notifications with optional filtering"""
    # Build query with user_id
    query = {"user_id": current_user["id"]}
    
    # Add is_read filter if specified
    if is_read is not None:
        query["is_read"] = is_read
    
    # Add type filter if specified
    if type:
        query["type"] = type
    
    # Get notifications with pagination
    notifications = await notifications_collection.find(query).sort(
        "created_at", -1
    ).skip(offset).limit(limit).to_list(length=limit)
    
    # Add id field for each notification
    for notification in notifications:
        notification["id"] = str(notification["_id"])
    
    return notifications

@router.get("/count")
async def get_unread_count(
    current_user = Depends(get_current_user)
):
    """Get count of unread notifications"""
    count = await notifications_collection.count_documents({
        "user_id": current_user["id"],
        "is_read": False
    })
    
    return {"unread_count": count}

@router.put("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user = Depends(get_current_user)
):
    """Mark a notification as read"""
    # Check if notification exists and belongs to the user
    notification = await notifications_collection.find_one({
        "_id": ObjectId(notification_id),
        "user_id": current_user["id"]
    })
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Mark as read
    await notifications_collection.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"is_read": True}}
    )
    
    return {"status": "success"}

@router.put("/read-all")
async def mark_all_read(
    current_user = Depends(get_current_user)
):
    """Mark all user notifications as read"""
    result = await notifications_collection.update_many(
        {"user_id": current_user["id"], "is_read": False},
        {"$set": {"is_read": True}}
    )
    
    return {"status": "success", "updated_count": result.modified_count}

@router.get("/settings", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    current_user = Depends(get_current_user)
):
    """Get user's notification settings"""
    settings = await notification_settings_collection.find_one({
        "user_id": current_user["id"]
    })
    
    if not settings:
        # Create default settings if none exist
        settings = {
            "user_id": current_user["id"],
            "meal_reminders": True,
            "weekly_report": True,
            "nutrition_tips": True,
            "progress_updates": True,
            "marketing": False,
            "reminder_times": {
                "breakfast": "08:00",
                "lunch": "12:00",
                "dinner": "18:00"
            },
            "created_at": datetime.utcnow()
        }
        result = await notification_settings_collection.insert_one(settings)
        settings["id"] = str(result.inserted_id)
    else:
        settings["id"] = str(settings["_id"])
    
    return settings

@router.put("/settings", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    settings_update: NotificationSettingsUpdate,
    current_user = Depends(get_current_user)
):
    """Update user's notification settings"""
    # Get current settings
    current_settings = await notification_settings_collection.find_one({
        "user_id": current_user["id"]
    })
    
    # Only update fields that are provided
    update_data = {k: v for k, v in settings_update.dict(exclude_unset=True).items() if v is not None}
    
    if current_settings:
        # Update existing settings
        await notification_settings_collection.update_one(
            {"user_id": current_user["id"]},
            {"$set": {**update_data, "updated_at": datetime.utcnow()}}
        )
    else:
        # Create new settings with defaults + updates
        default_settings = {
            "user_id": current_user["id"],
            "meal_reminders": True,
            "weekly_report": True,
            "nutrition_tips": True,
            "progress_updates": True,
            "marketing": False,
            "reminder_times": {
                "breakfast": "08:00",
                "lunch": "12:00",
                "dinner": "18:00"
            },
            "created_at": datetime.utcnow()
        }
        await notification_settings_collection.insert_one({**default_settings, **update_data})
    
    # Get updated settings
    updated_settings = await notification_settings_collection.find_one({
        "user_id": current_user["id"]
    })
    
    if updated_settings:
        updated_settings["id"] = str(updated_settings["_id"])
    
    return updated_settings

@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a notification"""
    # Check if notification exists and belongs to the user
    notification = await notifications_collection.find_one({
        "_id": ObjectId(notification_id),
        "user_id": current_user["id"]
    })
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Delete the notification
    await notifications_collection.delete_one({"_id": ObjectId(notification_id)})
    
    return {"status": "success", "deleted_id": notification_id}

# New notification creation endpoints for app features
@router.post("/create")
async def create_notification(
    title: str,
    message: str,
    notification_type: str,
    data: Optional[Dict] = None,
    current_user = Depends(get_current_user)
):
    """Create a new notification for the current user"""
    notification = {
        "user_id": current_user["id"],
        "title": title,
        "message": message,
        "type": notification_type,
        "is_read": False,
        "data": data or {},
        "created_at": datetime.utcnow()
    }
    
    result = await notifications_collection.insert_one(notification)
    
    return {
        "status": "success",
        "id": str(result.inserted_id),
        "notification": {**notification, "id": str(result.inserted_id)}
    }

@router.post("/meal-reminder")
async def create_meal_reminder(
    background_tasks: BackgroundTasks,
    meal_type: str = Query(..., description="Type of meal: breakfast, lunch, or dinner"),
    current_user = Depends(get_current_user)
):
    """Create a meal reminder notification"""
    # Get user settings to check if meal reminders are enabled
    settings = await notification_settings_collection.find_one({
        "user_id": current_user["id"]
    })
    
    if not settings or settings.get("meal_reminders", True):
        # Create reminder notification
        notification = {
            "user_id": current_user["id"],
            "title": f"Time for {meal_type}!",
            "message": f"Don't forget to log your {meal_type} for today.",
            "type": "meal_reminder",
            "is_read": False,
            "data": {"meal_type": meal_type},
            "created_at": datetime.utcnow()
        }
        
        background_tasks.add_task(
            notifications_collection.insert_one, notification
        )
        
        return {"status": "success", "message": f"{meal_type.capitalize()} reminder scheduled"}
    else:
        return {"status": "skipped", "message": "Meal reminders are disabled in user settings"}