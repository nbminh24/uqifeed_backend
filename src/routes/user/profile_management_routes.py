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
from src.utils.db_utils import (
    nutrition_targets_collection,
    safe_db_operation
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
    """Step 1: Set user's gender with atomic update"""
    try:
        result = await safe_db_operation(
            profiles_collection.update_one(
                {"user_id": current_user["id"]},
                {
                    "$set": {
                        "gender": gender,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        )
        
        if result.modified_count == 0 and not result.upserted_id:
            raise HTTPException(status_code=400, detail="Failed to update gender")
        
        return {"status": "success", "gender": gender}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/birthdate", response_model=dict)
async def set_birthdate(
    birthdate: date,
    current_user = Depends(get_current_user)
):
    """Step 2: Set user's birthdate with atomic update"""
    try:
        # Calculate age
        today = datetime.now().date()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        
        result = await safe_db_operation(
            profiles_collection.update_one(
                {"user_id": current_user["id"]},
                {
                    "$set": {
                        "birthdate": birthdate,
                        "age": age,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        )
        
        if result.modified_count == 0 and not result.upserted_id:
            raise HTTPException(status_code=400, detail="Failed to update birthdate")
        
        return {"status": "success", "birthdate": birthdate, "age": age}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/measurements", response_model=dict)
async def set_measurements(
    height: float,
    weight: float,
    current_user = Depends(get_current_user)
):
    """Step 3: Set user's height and weight with atomic update"""
    try:
        # Calculate BMI
        height_m = height / 100  # Convert cm to m
        bmi = round(weight / (height_m * height_m), 1)
        
        result = await safe_db_operation(
            profiles_collection.update_one(
                {"user_id": current_user["id"]},
                {
                    "$set": {
                        "height": height,
                        "weight": weight,
                        "bmi": bmi,
                        "bmi_category": get_bmi_category(bmi),
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        )
        
        if result.modified_count == 0 and not result.upserted_id:
            raise HTTPException(status_code=400, detail="Failed to update measurements")
        
        return {
            "status": "success", 
            "height": height, 
            "weight": weight, 
            "bmi": bmi,
            "bmi_category": get_bmi_category(bmi)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/goal", response_model=dict)
async def set_weight_goal(
    goal: WeightGoal,
    current_user = Depends(get_current_user)
):
    """Step 4: Set user's weight goal with atomic update"""
    try:
        result = await safe_db_operation(
            profiles_collection.update_one(
                {"user_id": current_user["id"]},
                {
                    "$set": {
                        "goal": goal,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        )
        
        if result.modified_count == 0 and not result.upserted_id:
            raise HTTPException(status_code=400, detail="Failed to update weight goal")
        
        return {"status": "success", "goal": goal}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/desired-weight", response_model=dict)
async def set_desired_weight(
    desired_weight: float,
    goal_duration_weeks: int,
    current_user = Depends(get_current_user)
):
    """Step 5: Set user's desired weight and timeframe with validation"""
    try:
        # Get current profile
        profile = await safe_db_operation(
            profiles_collection.find_one({"user_id": current_user["id"]})
        )
        
        if not profile:
            raise HTTPException(status_code=400, detail="Please complete previous steps first")
        
        # Validate weight goal
        current_weight = profile.get("weight")
        goal = profile.get("goal")
        
        if not current_weight or not goal:
            raise HTTPException(status_code=400, detail="Weight and goal must be set first")
        
        if goal == WeightGoal.MAINTAIN and desired_weight != current_weight:
            raise HTTPException(
                status_code=400,
                detail="Desired weight should match current weight for maintenance goal"
            )
        
        # Calculate weekly change
        weight_change = desired_weight - current_weight
        weekly_change = weight_change / goal_duration_weeks if goal_duration_weeks > 0 else 0
        
        # Validate weekly change
        if abs(weekly_change) > 1.0:
            raise HTTPException(
                status_code=400,
                detail="Weekly weight change is too aggressive (max 1kg per week)"
            )
        
        # Update profile
        result = await safe_db_operation(
            profiles_collection.update_one(
                {"user_id": current_user["id"]},
                {
                    "$set": {
                        "desired_weight": desired_weight,
                        "goal_duration_weeks": goal_duration_weeks,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to update desired weight")
        
        return {
            "status": "success", 
            "desired_weight": desired_weight, 
            "goal_duration_weeks": goal_duration_weeks,
            "weekly_change": round(weekly_change, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/activity-level", response_model=dict)
async def set_activity_level(
    activity_level: ActivityLevel,
    current_user = Depends(get_current_user)
):
    """Step 6: Set user's activity level with atomic update"""
    try:
        result = await safe_db_operation(
            profiles_collection.update_one(
                {"user_id": current_user["id"]},
                {
                    "$set": {
                        "activity_level": activity_level,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        )
        
        if result.modified_count == 0 and not result.upserted_id:
            raise HTTPException(status_code=400, detail="Failed to update activity level")
        
        return {"status": "success", "activity_level": activity_level}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/diet-type", response_model=dict)
async def set_diet_type(
    diet_type: DietType,
    current_user = Depends(get_current_user)
):
    """Step 7: Set user's diet type with atomic update"""
    try:
        result = await safe_db_operation(
            profiles_collection.update_one(
                {"user_id": current_user["id"]},
                {
                    "$set": {
                        "diet_type": diet_type,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        )
        
        if result.modified_count == 0 and not result.upserted_id:
            raise HTTPException(status_code=400, detail="Failed to update diet type")
        
        return {"status": "success", "diet_type": diet_type}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/additional-goals", response_model=dict)
async def set_additional_goals(
    additional_goals: List[AdditionalGoal],
    current_user = Depends(get_current_user)
):
    """Step 8: Set user's additional health goals with atomic update"""
    try:
        result = await safe_db_operation(
            profiles_collection.update_one(
                {"user_id": current_user["id"]},
                {
                    "$set": {
                        "additional_goals": additional_goals,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
        )
        
        if result.modified_count == 0 and not result.upserted_id:
            raise HTTPException(status_code=400, detail="Failed to update additional goals")
        
        return {"status": "success", "additional_goals": additional_goals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/complete", response_model=dict)
async def complete_profile(current_user = Depends(get_current_user)):
    """Finalize user profile and calculate nutrition targets"""
    try:
        # Get current profile
        profile = await safe_db_operation(
            profiles_collection.find_one({"user_id": current_user["id"]})
        )
        
        if not profile:
            raise HTTPException(status_code=400, detail="Please complete all profile steps first")
        
        # Validate required fields
        required_fields = [
            "gender", "birthdate", "height", "weight", 
            "goal", "activity_level", "diet_type"
        ]
        missing_fields = [
            field for field in required_fields 
            if field not in profile or profile[field] is None
        ]
        
        if missing_fields:
            raise HTTPException(
                status_code=400, 
                detail=f"Please complete these profile fields first: {', '.join(missing_fields)}"
            )
        
        # Validate weight goals
        if profile["goal"] in ["LOSE", "GAIN"]:
            if "desired_weight" not in profile or "goal_duration_weeks" not in profile:
                raise HTTPException(
                    status_code=400,
                    detail="Please set desired weight and goal duration for weight loss/gain"
                )
        
        # Set default additional goals if not set
        if "additional_goals" not in profile:
            profile["additional_goals"] = []
        
        # Update profile status
        result = await safe_db_operation(
            profiles_collection.update_one(
                {"user_id": current_user["id"]},
                {
                    "$set": {
                        "profile_completed": True,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail="Failed to complete profile")
        
        # Calculate nutrition targets
        nutrition_target = await create_or_update_nutrition_target(current_user["id"])
        
        return {
            "status": "success",
            "profile": profile,
            "nutrition_target": nutrition_target
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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