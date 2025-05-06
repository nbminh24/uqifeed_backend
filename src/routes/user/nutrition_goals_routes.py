from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime

from src.config.database import profiles_collection, nutrition_targets_collection
from src.services.authentication.user_auth import get_current_user
from src.services.nutrition.nutrition_calculator import create_or_update_nutrition_target, calculate_progress_projection
from src.schemas.nutrition.nutrition_schema import NutritionTargetResponse, ProgressProjection

# Initialize router
router = APIRouter(
    tags=["nutrition-goals"]
)

@router.post("/complete", response_model=dict)
async def complete_profile(
    current_user = Depends(get_current_user)
):
    """Finalize user profile and calculate nutrition targets"""
    # Check if user has a profile with all required fields
    profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    
    if not profile:
        raise HTTPException(status_code=400, detail="Please complete all profile steps first")
    
    required_fields = ["gender", "birthdate", "height", "weight", "goal", "activity_level", "diet_type"]
    missing_fields = [field for field in required_fields if field not in profile or profile[field] is None]
    
    if missing_fields:
        raise HTTPException(
            status_code=400, 
            detail=f"Please complete these profile fields first: {', '.join(missing_fields)}"
        )
    
    # If goal is to lose or gain, ensure desired weight and timeframe are set
    if profile["goal"] in ["LOSE", "GAIN"]:
        if "desired_weight" not in profile or "goal_duration_weeks" not in profile:
            raise HTTPException(
                status_code=400,
                detail="Please set desired weight and goal duration for weight loss/gain"
            )
    
    # Ensure all fields are present (use defaults if needed)
    if "additional_goals" not in profile:
        profile["additional_goals"] = []
    
    # Calculate nutrition targets based on completed profile
    await create_or_update_nutrition_target(current_user["id"])
    
    # Add id field for Pydantic model
    if "_id" in profile:
        profile["id"] = str(profile["_id"])
    
    return profile

@router.get("/summary", response_model=dict)
async def get_profile_summary(
    current_user = Depends(get_current_user)
):
    """Get user profile summary with nutrition targets and progress projection"""
    # Get user profile
    profile = await profiles_collection.find_one({"user_id": current_user["id"]})
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Get nutrition targets
    target = await nutrition_targets_collection.find_one({"user_id": current_user["id"]})
    if not target:
        raise HTTPException(status_code=404, detail="Nutrition target not found")
    
    # Calculate progress projection
    projection = None
    if profile.get("goal") in ["LOSE", "GAIN"] and profile.get("desired_weight") and profile.get("goal_duration_weeks"):
        projection = await calculate_progress_projection(
            start_weight=profile["weight"],
            desired_weight=profile["desired_weight"],
            goal_duration_weeks=profile["goal_duration_weeks"]
        )
    
    # Convert ObjectId to string
    if "_id" in profile:
        profile["id"] = str(profile["_id"])
    if "_id" in target:
        target["id"] = str(target["_id"])
    
    # Calculate BMI
    height_m = profile["height"] / 100  # Convert cm to m
    bmi = round(profile["weight"] / (height_m * height_m), 1)
    
    return {
        "profile": profile,
        "nutrition_target": target,
        "progress_projection": projection,
        "bmi": bmi,
        "bmi_category": get_bmi_category(bmi)
    }

@router.get("/target", response_model=NutritionTargetResponse)
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

# Helper function for BMI calculation
def get_bmi_category(bmi: float) -> str:
    """Return the BMI category for a given BMI value"""
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal weight"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obesity"