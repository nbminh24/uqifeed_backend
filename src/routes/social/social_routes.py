from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from src.services.social.social_sharing import (
    share_achievement,
    share_meal,
    share_progress,
    get_shared_posts
)
from src.services.authentication.user_auth import get_current_user
from src.schemas.social.social_schema import (
    ShareAchievementRequest,
    ShareMealRequest,
    ShareProgressRequest
)

router = APIRouter(
    prefix="/social",
    tags=["social"]
)

@router.post("/share/achievement")
async def share_achievement_endpoint(
    request: ShareAchievementRequest,
    current_user = Depends(get_current_user)
):
    """Share an achievement"""
    result = await share_achievement(
        current_user["id"],
        request.achievement_type,
        request.achievement_data
    )
    if not result:
        raise HTTPException(status_code=400, detail="Failed to share achievement")
    return result

@router.post("/share/meal")
async def share_meal_endpoint(
    request: ShareMealRequest,
    current_user = Depends(get_current_user)
):
    """Share a meal"""
    result = await share_meal(
        current_user["id"],
        request.meal_id,
        request.meal_data
    )
    if not result:
        raise HTTPException(status_code=400, detail="Failed to share meal")
    return result

@router.post("/share/progress")
async def share_progress_endpoint(
    request: ShareProgressRequest,
    current_user = Depends(get_current_user)
):
    """Share progress"""
    result = await share_progress(
        current_user["id"],
        request.progress_type,
        request.progress_data
    )
    if not result:
        raise HTTPException(status_code=400, detail="Failed to share progress")
    return result

@router.get("/posts")
async def get_posts_endpoint(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    current_user = Depends(get_current_user)
):
    """Get shared posts"""
    result = await get_shared_posts(current_user["id"], page, limit)
    return result 