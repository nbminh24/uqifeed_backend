from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from src.config.database import get_db, notifications_collection, notification_settings_collection
from src.schemas.schemas import NotificationResponse, NotificationSettingsResponse, NotificationSettingsUpdate
from src.services.auth_service import get_current_user

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
    dependencies=[Depends(get_current_user)]  # All routes require authentication
)

@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(
    limit: int = 20,
    offset: int = 0,
    is_read: Optional[bool] = None,
    current_user = Depends(get_current_user)
):
    """Get user notifications with optional filtering"""
    # Build query with user_id
    query = {"user_id": current_user["id"]}
    
    # Add is_read filter if specified
    if is_read is not None:
        query["is_read"] = is_read
    
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
    # Check if notification exists and belongs to user
    notification = await notifications_collection.find_one({
        "_id": ObjectId(notification_id),
        "user_id": current_user["id"]
    })
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Update notification
    await notifications_collection.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
    )
    
    return {"message": "Notification marked as read"}

@router.put("/read-all")
async def mark_all_read(
    current_user = Depends(get_current_user)
):
    """Mark all notifications as read"""
    await notifications_collection.update_many(
        {
            "user_id": current_user["id"],
            "is_read": False
        },
        {"$set": {"is_read": True, "read_at": datetime.utcnow()}}
    )
    
    return {"message": "All notifications marked as read"}

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
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await notification_settings_collection.insert_one(default_settings)
        settings = await notification_settings_collection.find_one({"_id": result.inserted_id})
    
    # Add id field for Pydantic model
    settings["id"] = str(settings["_id"])
    
    return settings

@router.put("/settings", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    settings_data: NotificationSettingsUpdate,
    current_user = Depends(get_current_user)
):
    """Update user's notification settings"""
    # Check if settings exist
    existing_settings = await notification_settings_collection.find_one({
        "user_id": current_user["id"]
    })
    
    # Update data
    update_data = {k: v for k, v in settings_data.dict(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    if not existing_settings:
        # Create settings if none exist
        update_data["user_id"] = current_user["id"]
        update_data["created_at"] = datetime.utcnow()
        
        result = await notification_settings_collection.insert_one(update_data)
        updated_settings = await notification_settings_collection.find_one({"_id": result.inserted_id})
    else:
        # Update existing settings
        await notification_settings_collection.update_one(
            {"user_id": current_user["id"]},
            {"$set": update_data}
        )
        updated_settings = await notification_settings_collection.find_one({"user_id": current_user["id"]})
    
    # Add id field for Pydantic model
    updated_settings["id"] = str(updated_settings["_id"])
    
    return updated_settings

@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a notification"""
    # Check if notification exists and belongs to user
    notification = await notifications_collection.find_one({
        "_id": ObjectId(notification_id),
        "user_id": current_user["id"]
    })
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    # Delete notification
    await notifications_collection.delete_one({"_id": ObjectId(notification_id)})
    
    return {"message": "Notification deleted successfully"}