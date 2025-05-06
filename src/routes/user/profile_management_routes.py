from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, date
from typing import List

from src.config.database import profiles_collection
from src.services.authentication.user_auth import get_current_user
from src.services.user.profile_manager import get_bmi_category
from src.schemas.user.profile_schema import (
    ProfileNutritionCreate, 
    ProfileNutritionUpdate, 
    ProfileNutritionResponse,
    Gender, 
    ActivityLevel,
    WeightGoal, 
    DietType, 
    AdditionalGoal
)

# Initialize router
router = APIRouter(
    tags=["profile"]
)

# Step-by-step profile creation endpoints
@router.post("/gender", response_model=dict)
async def set_gender(
    gender: Gender,
    current_user = Depends(get_current_user)
):
    """Step 1: Set user's gender"""
    # Check if user has a profile
    profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    
    if profile:
        # Update existing profile
        await profiles_collection.update_one(
            {"user_id": current_user["id"]},
            {"$set": {"gender": gender, "updated_at": datetime.utcnow()}}
        )
    else:
        # Create a new profile with just the gender
        await profiles_collection.insert_one({
            "user_id": current_user["id"],
            "gender": gender,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    
    return {"status": "success", "gender": gender}

@router.post("/birthdate", response_model=dict)
async def set_birthdate(
    birthdate: date,
    current_user = Depends(get_current_user)
):
    """Step 2: Set user's birthdate"""
    # Calculate age
    today = datetime.now().date()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    
    # Check if user has a profile
    profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    
    if profile:
        # Update existing profile
        await profiles_collection.update_one(
            {"user_id": current_user["id"]},
            {"$set": {"birthdate": birthdate, "updated_at": datetime.utcnow()}}
        )
    else:
        # Create a new profile with just the birthdate
        await profiles_collection.insert_one({
            "user_id": current_user["id"],
            "birthdate": birthdate,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    
    return {"status": "success", "birthdate": birthdate, "age": age}

@router.post("/measurements", response_model=dict)
async def set_measurements(
    height: float,
    weight: float,
    current_user = Depends(get_current_user)
):
    """Step 3: Set user's height and weight"""
    # Calculate BMI
    height_m = height / 100  # Convert cm to m
    bmi = round(weight / (height_m * height_m), 1)
    
    # Check if user has a profile
    profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    
    if profile:
        # Update existing profile
        await profiles_collection.update_one(
            {"user_id": current_user["id"]},
            {"$set": {
                "height": height, 
                "weight": weight,
                "updated_at": datetime.utcnow()
            }}
        )
    else:
        # Create a new profile with measurements
        await profiles_collection.insert_one({
            "user_id": current_user["id"],
            "height": height,
            "weight": weight,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    
    return {
        "status": "success", 
        "height": height, 
        "weight": weight, 
        "bmi": bmi,
        "bmi_category": get_bmi_category(bmi)
    }

@router.post("/goal", response_model=dict)
async def set_weight_goal(
    goal: WeightGoal,
    current_user = Depends(get_current_user)
):
    """Step 4: Set user's weight goal (lose/maintain/gain)"""
    # Check if user has a profile
    profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    
    if not profile:
        raise HTTPException(status_code=400, detail="Please complete previous steps first")
    
    # Update profile
    await profiles_collection.update_one(
        {"user_id": current_user["id"]},
        {"$set": {"goal": goal, "updated_at": datetime.utcnow()}}
    )
    
    return {"status": "success", "goal": goal}

@router.post("/desired-weight", response_model=dict)
async def set_desired_weight(
    desired_weight: float,
    goal_duration_weeks: int,
    current_user = Depends(get_current_user)
):
    """Step 5: Set user's desired weight and timeframe"""
    # Check if user has a profile
    profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    
    if not profile:
        raise HTTPException(status_code=400, detail="Please complete previous steps first")
    
    # Get current weight and goal
    current_weight = profile.get("weight")
    goal = profile.get("goal")
    
    if not current_weight or not goal:
        raise HTTPException(status_code=400, detail="Weight and goal must be set first")
    
    if goal == WeightGoal.MAINTAIN and desired_weight != current_weight:
        raise HTTPException(status_code=400, detail="Desired weight should match current weight for maintenance goal")
    
    weight_change = desired_weight - current_weight
    weekly_change = weight_change / goal_duration_weeks if goal_duration_weeks > 0 else 0
    
    # Update profile
    await profiles_collection.update_one(
        {"user_id": current_user["id"]},
        {"$set": {
            "desired_weight": desired_weight,
            "goal_duration_weeks": goal_duration_weeks,
            "updated_at": datetime.utcnow()
        }}
    )
    
    return {
        "status": "success", 
        "desired_weight": desired_weight, 
        "goal_duration_weeks": goal_duration_weeks,
        "weekly_change": round(weekly_change, 2)
    }

@router.post("/activity-level", response_model=dict)
async def set_activity_level(
    activity_level: ActivityLevel,
    current_user = Depends(get_current_user)
):
    """Step 6: Set user's activity level"""
    # Check if user has a profile
    profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    
    if not profile:
        raise HTTPException(status_code=400, detail="Please complete previous steps first")
    
    # Update profile
    await profiles_collection.update_one(
        {"user_id": current_user["id"]},
        {"$set": {"activity_level": activity_level, "updated_at": datetime.utcnow()}}
    )
    
    return {"status": "success", "activity_level": activity_level}

@router.post("/diet-type", response_model=dict)
async def set_diet_type(
    diet_type: DietType,
    current_user = Depends(get_current_user)
):
    """Step 7: Set user's diet type"""
    # Check if user has a profile
    profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    
    if not profile:
        raise HTTPException(status_code=400, detail="Please complete previous steps first")
    
    # Update profile
    await profiles_collection.update_one(
        {"user_id": current_user["id"]},
        {"$set": {"diet_type": diet_type, "updated_at": datetime.utcnow()}}
    )
    
    return {"status": "success", "diet_type": diet_type}

@router.post("/additional-goals", response_model=dict)
async def set_additional_goals(
    additional_goals: List[AdditionalGoal],
    current_user = Depends(get_current_user)
):
    """Step 8: Set user's additional health goals"""
    # Check if user has a profile
    profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    
    if not profile:
        raise HTTPException(status_code=400, detail="Please complete previous steps first")
    
    # Update profile
    await profiles_collection.update_one(
        {"user_id": current_user["id"]},
        {"$set": {"additional_goals": additional_goals, "updated_at": datetime.utcnow()}}
    )
    
    return {"status": "success", "additional_goals": additional_goals}

@router.post("", response_model=ProfileNutritionResponse)
async def create_profile(
    profile: ProfileNutritionCreate, 
    current_user = Depends(get_current_user)
):
    """Create user profile in one step"""
    # Check if user already has a profile
    existing_profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    if existing_profile:
        raise HTTPException(status_code=400, detail="User profile already exists")
    
    # Create new profile
    db_profile = {
        "user_id": current_user["id"],
        "gender": profile.gender,
        "birthdate": profile.birthdate,
        "height": profile.height,
        "weight": profile.weight,
        "desired_weight": profile.desired_weight,
        "goal_duration_weeks": profile.goal_duration_weeks,
        "activity_level": profile.activity_level,
        "goal": profile.goal,
        "diet_type": profile.diet_type,
        "additional_goals": profile.additional_goals,
        "updated_at": datetime.utcnow()
    }
    
    result = await profiles_collection.insert_one(db_profile)
    created_profile = await profiles_collection.find_one({"_id": result.inserted_id})
    
    # Add id field for Pydantic model
    if created_profile:
        created_profile["id"] = str(created_profile["_id"])
    
    return created_profile

@router.put("", response_model=ProfileNutritionResponse)
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
    
    # Add id field for Pydantic model
    if updated_profile:
        updated_profile["id"] = str(updated_profile["_id"])
    
    return updated_profile

@router.get("", response_model=ProfileNutritionResponse)
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