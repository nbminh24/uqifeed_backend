from datetime import datetime
from typing import Optional, Dict, Any
from bson import ObjectId

from src.config.database import profiles_collection

async def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a user's profile
    
    Args:
        user_id: User ID
    
    Returns:
        Optional[Dict]: User profile if found, None otherwise
    """
    profile = await profiles_collection.find_one({"user_id": user_id})
    if profile and "_id" in profile:
        profile["id"] = str(profile["_id"])
    return profile

async def update_profile_field(user_id: str, field: str, value: Any) -> Dict[str, Any]:
    """
    Update a single field in a user's profile
    
    Args:
        user_id: User ID
        field: Field name to update
        value: New value for field
    
    Returns:
        Dict: Update status
    """
    # Check if user has a profile
    profile = await profiles_collection.find_one({"user_id": user_id})
    
    if profile:
        # Update existing profile
        await profiles_collection.update_one(
            {"user_id": user_id},
            {"$set": {field: value, "updated_at": datetime.utcnow()}}
        )
    else:
        # Create a new profile with the field
        await profiles_collection.insert_one({
            "user_id": user_id,
            field: value,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    
    return {"status": "success", field: value}