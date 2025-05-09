from datetime import datetime
from typing import Dict, List, Any, Optional
import math

from src.config.database import profiles_collection, nutrition_targets_collection
from src.services.user.profile_manager import get_user_profile
from src.schemas.nutrition.nutrition_schema import ProgressProjection

async def calculate_bmr(profile: Dict[str, Any]) -> float:
    """
    Calculate Basal Metabolic Rate (BMR) using the Mifflin-St Jeor Equation
    
    Args:
        profile: User profile data
    
    Returns:
        float: Calculated BMR
    """
    # Extract profile data
    weight = profile.get("weight", 0)  # kg
    height = profile.get("height", 0)  # cm
    birthdate = profile.get("birthdate")
    gender = profile.get("gender")
    
    # Calculate age from birthdate
    today = datetime.now().date()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    
    # Calculate BMR using Mifflin-St Jeor Equation
    if gender == "MALE":
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:  # FEMALE
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    
    return round(bmr)

async def calculate_tdee(bmr: float, activity_level: str) -> float:
    """
    Calculate Total Daily Energy Expenditure (TDEE)
    
    Args:
        bmr: Basal Metabolic Rate
        activity_level: Activity level
    
    Returns:
        float: Calculated TDEE
    """
    # Activity multiplier based on activity level
    activity_multipliers = {
        "SEDENTARY": 1.2,
        "LIGHTLY_ACTIVE": 1.375,
        "MODERATELY_ACTIVE": 1.55,
        "VERY_ACTIVE": 1.725,
        "EXTRA_ACTIVE": 1.9
    }
    
    multiplier = activity_multipliers.get(activity_level, 1.2)
    tdee = bmr * multiplier
    
    return round(tdee)

async def calculate_macros(tdee: float, goal: str, diet_type: str, profile: Dict[str, Any]) -> Dict[str, int]:
    """
    Calculate macronutrient targets based on TDEE, user goals, and diet type
    
    Args:
        tdee: Total Daily Energy Expenditure
        goal: Weight goal (LOSE, MAINTAIN, GAIN)
        diet_type: Diet type
        profile: User profile containing gender and age
    
    Returns:
        Dict: Calculated macronutrient targets
    """
    # Adjust calories based on goal
    if goal == "LOSE":
        calorie_target = tdee - 500  # 500 calorie deficit
    elif goal == "GAIN":
        calorie_target = tdee + 500  # 500 calorie surplus
    else:  # MAINTAIN
        calorie_target = tdee
    
    # Base macro distribution (protein/carbs/fat) based on diet type
    # Format: (carbs_ratio, protein_ratio, fat_ratio)
    macro_ratios = {
        "BALANCED": (0.50, 0.20, 0.30),
        "VEGETARIAN": (0.55, 0.15, 0.30),
        "VEGAN": (0.60, 0.15, 0.25),
        "PALEO": (0.30, 0.30, 0.40),
        "KETO": (0.05, 0.20, 0.75),
        "HIGH_PROTEIN": (0.25, 0.35, 0.40),
        "LOW_CARB": (0.20, 0.30, 0.50),
        # Default to balanced if not specified
        "STANDARD": (0.50, 0.20, 0.30)
    }
    
    carbs_ratio, protein_ratio, fat_ratio = macro_ratios.get(diet_type, macro_ratios["STANDARD"])
    
    # Calculate macros in grams
    protein_cals = calorie_target * protein_ratio
    carbs_cals = calorie_target * carbs_ratio
    fat_cals = calorie_target * fat_ratio
    
    protein_g = round(protein_cals / 4)  # 4 calories per gram of protein
    carbs_g = round(carbs_cals / 4)      # 4 calories per gram of carbs
    fat_g = round(fat_cals / 9)          # 9 calories per gram of fat
    
    # Calculate fiber based on gender and age
    gender = profile.get("gender", "MALE")
    birthdate = profile.get("birthdate")
    
    # Calculate age
    today = datetime.now().date()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    
    # Determine fiber based on age and gender according to guidelines
    fiber_g = 25  # Default value
    
    if age >= 18:
        if age <= 50:
            fiber_g = 38 if gender == "MALE" else 25
        else:  # age > 50
            fiber_g = 30 if gender == "MALE" else 21
    else:  # Under 18
        if age <= 3:
            fiber_g = 19
        elif age <= 8:
            fiber_g = 25
        elif age <= 13:
            fiber_g = 26 if gender == "MALE" else 24
        else:  # age <= 18
            fiber_g = 38 if gender == "MALE" else 26
    
    # Calculate water recommendation (ml = weight in kg * 30)
    weight_kg = profile.get("weight", 70)
    water_ml = round(weight_kg * 30)
    
    return {
        "calories": round(calorie_target),
        "protein": protein_g,
        "carb": carbs_g,  # Đã sửa từ carbs sang carb để khớp với database
        "fat": fat_g,
        "fiber": fiber_g,
        "water": water_ml
    }

async def calculate_meal_distribution(daily_calories: float) -> Dict[str, Dict[str, float]]:
    """
    Calculate nutrition distribution for each meal type
    
    Args:
        daily_calories: Total daily calorie target
    
    Returns:
        Dict containing nutrition targets for each meal type
    """
    # Standard meal distribution percentages
    meal_distribution = {
        "breakfast": {
            "calories_percentage": 25,  # 25% of daily calories
            "protein_percentage": 25,
            "carb_percentage": 30,
            "fat_percentage": 25,
            "fiber_percentage": 25
        },
        "lunch": {
            "calories_percentage": 35,  # 35% of daily calories
            "protein_percentage": 35,
            "carb_percentage": 35,
            "fat_percentage": 35,
            "fiber_percentage": 35
        },
        "dinner": {
            "calories_percentage": 30,  # 30% of daily calories
            "protein_percentage": 30,
            "carb_percentage": 25,
            "fat_percentage": 30,
            "fiber_percentage": 30
        },
        "snack": {
            "calories_percentage": 10,  # 10% of daily calories
            "protein_percentage": 10,
            "carb_percentage": 10,
            "fat_percentage": 10,
            "fiber_percentage": 10
        }
    }
    
    # Calculate actual values for each meal type
    meal_targets = {}
    for meal_type, percentages in meal_distribution.items():
        meal_targets[meal_type] = {
            "calories": round(daily_calories * (percentages["calories_percentage"] / 100)),
            "protein_percentage": percentages["protein_percentage"],
            "carb_percentage": percentages["carb_percentage"],
            "fat_percentage": percentages["fat_percentage"],
            "fiber_percentage": percentages["fiber_percentage"]
        }
    
    return meal_targets

async def create_or_update_nutrition_target(user_id: str) -> Dict[str, Any]:
    """
    Create or update a user's nutrition targets
    
    Args:
        user_id: User ID
    
    Returns:
        Dict: Created or updated nutrition targets
    """
    # Get user profile
    profile = await get_user_profile(user_id)
    if not profile:
        return {"error": "User profile not found"}
    
    # Calculate BMR and TDEE
    bmr = await calculate_bmr(profile)
    tdee = await calculate_tdee(bmr, profile["activity_level"])
    
    # Calculate macros
    macros = await calculate_macros(tdee, profile["goal"], profile["diet_type"], profile)
    
    # Calculate meal distribution
    meal_distribution = await calculate_meal_distribution(macros["calories"])
    
    # Prepare nutrition target data
    target_data = {
        "user_id": user_id,
        "bmr": bmr,
        "tdee": tdee,
        "calories": macros["calories"],
        "protein": macros["protein"],
        "carb": macros["carb"],
        "fat": macros["fat"],
        "fiber": macros["fiber"],
        "water": macros["water"],
        "meal_distribution": meal_distribution,
        "updated_at": datetime.utcnow()
    }
    
    # Check if target already exists
    existing_target = await nutrition_targets_collection.find_one({"user_id": user_id})
    
    if existing_target:
        # Update existing target
        await nutrition_targets_collection.update_one(
            {"user_id": user_id},
            {"$set": target_data}
        )
    else:
        # Create new target
        target_data["created_at"] = datetime.utcnow()
        await nutrition_targets_collection.insert_one(target_data)
    
    # Get the updated target
    updated_target = await nutrition_targets_collection.find_one({"user_id": user_id})
    if updated_target:
        updated_target["id"] = str(updated_target["_id"])
    
    return updated_target

async def calculate_progress_projection(
    start_weight: float, 
    desired_weight: float, 
    goal_duration_weeks: int
) -> ProgressProjection:
    """
    Calculate weight progress projection over time
    
    Args:
        start_weight: Starting weight
        desired_weight: Desired weight
        goal_duration_weeks: Number of weeks for the goal
    
    Returns:
        ProgressProjection: Weekly weight projections
    """
    if goal_duration_weeks <= 0:
        return None
    
    # Calculate weekly change
    total_change = desired_weight - start_weight
    weekly_change = total_change / goal_duration_weeks
    
    # Generate weekly projections
    weekly_projections = []
    for week in range(goal_duration_weeks + 1):
        projected_weight = start_weight + (weekly_change * week)
        weekly_projections.append({
            "week": week,
            "weight": round(projected_weight, 1)
        })
    
    return {
        "start_weight": start_weight,
        "desired_weight": desired_weight,
        "goal_duration_weeks": goal_duration_weeks,
        "weekly_change": round(weekly_change, 2),
        "weekly_projections": weekly_projections
    }

async def evaluate_fiber_intake(fiber_intake: float, target_fiber: float) -> Dict[str, Any]:
    """
    Evaluate fiber intake against target and provide feedback
    
    Args:
        fiber_intake: Actual fiber intake in grams
        target_fiber: Target fiber intake in grams
    
    Returns:
        Dict: Evaluation results with feedback
    """
    percentage = (fiber_intake / target_fiber) * 100 if target_fiber > 0 else 0
    
    if percentage >= 100:
        status = "EXCELLENT"
        feedback = "Great job! You're meeting or exceeding your fiber target. This helps maintain digestive health and can reduce the risk of chronic diseases."
    elif percentage >= 80:
        status = "GOOD"
        feedback = "Good fiber intake. Consider adding a bit more fiber-rich foods to reach your target."
    elif percentage >= 60:
        status = "MODERATE"
        feedback = "Moderate fiber intake. Try to include more fruits, vegetables, and whole grains in your diet."
    else:
        status = "LOW"
        feedback = "Low fiber intake. Increase your consumption of fiber-rich foods like fruits, vegetables, legumes, and whole grains."
    
    return {
        "status": status,
        "percentage": round(percentage, 1),
        "feedback": feedback,
        "intake": round(fiber_intake, 1),
        "target": round(target_fiber, 1)
    }