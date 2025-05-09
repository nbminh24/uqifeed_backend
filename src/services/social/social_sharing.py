from typing import Dict, Any, Optional
from datetime import date, datetime
import logging
from src.services.calorie.calorie_service import get_weekly_statistics
from src.services.user.profile_manager import get_user_profile
from src.utils.db_utils import safe_db_operation
from src.config.database import shared_posts_collection
from fastapi import HTTPException

logger = logging.getLogger(__name__)

VALID_PRIVACY_SETTINGS = ["public", "friends", "private"]
VALID_SHARE_TYPES = ["achievement", "meal", "progress"]

async def create_shareable_post(
    user_id: str,
    share_type: str,
    content: Dict[str, Any],
    privacy: str = "public"
) -> Dict[str, Any]:
    """
    Create a shareable post with validation
    """
    try:
        # Validate inputs
        if privacy not in VALID_PRIVACY_SETTINGS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid privacy setting. Must be one of: {VALID_PRIVACY_SETTINGS}"
            )
            
        if share_type not in VALID_SHARE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid share type. Must be one of: {VALID_SHARE_TYPES}"
            )
            
        if not content:
            raise HTTPException(
                status_code=400,
                detail="Content cannot be empty"
            )
            
        # Get user profile
        user = await get_user_profile(user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
        # Create post
        post = {
            "user_id": user_id,
            "user_name": user.get("name", "Anonymous"),
            "share_type": share_type,
            "content": content,
            "privacy": privacy,
            "created_at": datetime.utcnow(),
            "likes": 0,
            "comments": []
        }
        
        # Save to database
        result = await safe_db_operation(
            shared_posts_collection.insert_one(post)
        )
        
        if result.inserted_id:
            post["id"] = str(result.inserted_id)
            return post
            
        raise HTTPException(
            status_code=500,
            detail="Failed to create post"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating shareable post: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

async def share_achievement(
    user_id: str,
    achievement_type: str,
    achievement_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Share an achievement with validation
    """
    if not achievement_type:
        raise HTTPException(
            status_code=400,
            detail="Achievement type is required"
        )
        
    if not achievement_data:
        raise HTTPException(
            status_code=400,
            detail="Achievement data is required"
        )
        
    content = {
        "type": "achievement",
        "achievement_type": achievement_type,
        "data": achievement_data
    }
    
    return await create_shareable_post(user_id, "achievement", content)

async def share_meal(
    user_id: str,
    meal_id: str,
    meal_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Share a meal with validation
    """
    if not meal_id:
        raise HTTPException(
            status_code=400,
            detail="Meal ID is required"
        )
        
    if not meal_data:
        raise HTTPException(
            status_code=400,
            detail="Meal data is required"
        )
        
    if not meal_data.get("name"):
        raise HTTPException(
            status_code=400,
            detail="Meal name is required"
        )
        
    content = {
        "type": "meal",
        "meal_id": meal_id,
        "data": meal_data
    }
    
    return await create_shareable_post(user_id, "meal", content)

async def share_progress(
    user_id: str,
    progress_type: str,
    progress_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    Share progress with validation
    """
    if not progress_type:
        raise HTTPException(
            status_code=400,
            detail="Progress type is required"
        )
        
    if not progress_data:
        raise HTTPException(
            status_code=400,
            detail="Progress data is required"
        )
        
    content = {
        "type": "progress",
        "progress_type": progress_type,
        "data": progress_data
    }
    
    return await create_shareable_post(user_id, "progress", content)

async def get_shared_posts(
    user_id: str,
    page: int = 1,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Get shared posts with validation
    """
    try:
        if page < 1:
            raise HTTPException(
                status_code=400,
                detail="Page number must be greater than 0"
            )
            
        if limit < 1 or limit > 50:
            raise HTTPException(
                status_code=400,
                detail="Limit must be between 1 and 50"
            )
            
        skip = (page - 1) * limit
        
        # Get posts
        posts = await safe_db_operation(
            shared_posts_collection.find(
                {"privacy": "public"}
            )
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        
        # Get total count
        total = await safe_db_operation(
            shared_posts_collection.count_documents({"privacy": "public"})
        )
        
        return {
            "posts": list(posts),
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting shared posts: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        ) 