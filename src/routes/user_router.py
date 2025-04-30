from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from typing import Optional

from src.config.database import get_db, users_collection, profiles_collection, nutrition_targets_collection
from src.schemas.schemas import (
    UserCreate, UserResponse, 
    ProfileNutritionCreate, ProfileNutritionUpdate, ProfileNutritionResponse,
    NutritionTargetResponse
)
from src.services.auth_service import (
    create_user, authenticate_user, create_access_token, 
    get_current_user, get_user_token_preference, set_user_token_preference
)
from src.services.nutrition_service import create_or_update_nutrition_target

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

# Public routes (no authentication required)
@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    """Register a new user"""
    return await create_user(user)

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session_type: Optional[str] = Query(None, description="Session duration preference: 'short', 'default', 'extended', or 'long'")
):
    """Login and get access token with configurable expiration time"""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # If session_type is provided, use it, otherwise get stored preference
    token_preference = session_type
    if not token_preference:
        token_preference = await get_user_token_preference(user["id"])
    
    # Create token with user preference
    access_token = create_access_token(
        data={"sub": user["email"]},
        user_preference=token_preference
    )
    
    # If user provided a session type preference, save it for future logins
    if session_type:
        await set_user_token_preference(user["id"], session_type)
    
    return {
        "access_token": access_token, 
        "token_type": "bearer", 
        "user_id": user["id"], 
        "name": user["name"],
        "session_type": token_preference
    }

@router.post("/token-preference")
async def update_token_preference(
    preference: str = Query(..., description="Session preference: 'short', 'default', 'extended', or 'long'"),
    current_user = Depends(get_current_user)
):
    """Update user's token expiration preference for future logins"""
    result = await set_user_token_preference(current_user["id"], preference)
    return result

# Protected routes (authentication required)
@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user = Depends(get_current_user)):
    """Get current user's information"""
    return current_user

@router.post("/profile", response_model=ProfileNutritionResponse)
async def create_profile(
    profile: ProfileNutritionCreate, 
    current_user = Depends(get_current_user)
):
    """Create user profile"""
    # Check if user already has a profile
    existing_profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    if existing_profile:
        raise HTTPException(status_code=400, detail="User profile already exists")
    
    # Create new profile
    db_profile = {
        "user_id": current_user["id"],
        "gender": profile.gender,
        "age": profile.age,
        "height": profile.height,
        "weight": profile.weight,
        "desired_weight": profile.desired_weight,
        "goal_duration_weeks": profile.goal_duration_weeks,
        "activity_level": profile.activity_level,
        "goal": profile.goal,
        "diet_type": profile.diet_type,
        "updated_at": datetime.utcnow()
    }
    
    result = await profiles_collection.insert_one(db_profile)
    created_profile = await profiles_collection.find_one({"_id": result.inserted_id})
    
    # Calculate and save nutrition targets
    await create_or_update_nutrition_target(current_user["id"])
    
    # Add id field for Pydantic model
    if created_profile:
        created_profile["id"] = str(created_profile["_id"])
    
    return created_profile

@router.put("/profile", response_model=ProfileNutritionResponse)
async def update_profile(
    profile_update: ProfileNutritionUpdate,
    current_user = Depends(get_current_user)
):
    """Update user profile"""
    # Get existing profile
    db_profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    if not db_profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Update profile fields
    update_data = {k: v for k, v in profile_update.dict(exclude_unset=True).items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await profiles_collection.update_one(
            {"user_id": current_user["id"]},
            {"$set": update_data}
        )
    
    # Get the updated profile
    updated_profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    
    # Update nutrition targets based on new profile
    await create_or_update_nutrition_target(current_user["id"])
    
    # Add id field for Pydantic model
    if updated_profile:
        updated_profile["id"] = str(updated_profile["_id"])
    
    return updated_profile

@router.get("/profile", response_model=ProfileNutritionResponse)
async def get_profile(
    current_user = Depends(get_current_user)
):
    """Get user profile"""
    db_profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    if not db_profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Add id field for Pydantic model
    if db_profile:
        db_profile["id"] = str(db_profile["_id"])
    
    return db_profile

@router.get("/nutrition-target", response_model=NutritionTargetResponse)
async def get_nutrition_target(
    current_user = Depends(get_current_user)
):
    """Get user's nutrition target"""
    target = await nutrition_targets_collection.find_one({"user_id": current_user["id"]})
    if not target:
        raise HTTPException(status_code=404, detail="Nutrition target not found")
    
    # Add id field for Pydantic model
    if target:
        target["id"] = str(target["_id"])
    
    return target