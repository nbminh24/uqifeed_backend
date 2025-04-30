from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import HTTPException

from src.config.database import profiles_collection, nutrition_targets_collection
from src.schemas.schemas import NutritionTargetCreate

def calculate_bmr(gender: str, weight: float, height: float, age: int) -> float:
    """
    Calculate Basal Metabolic Rate (BMR) using the Mifflin-St Jeor Equation
    
    For men: BMR = 10W + 6.25H - 5A + 5
    For women: BMR = 10W + 6.25H - 5A - 161
    
    W is body weight in kg, H is body height in cm, A is age
    """
    if gender == "male":
        return 10 * weight + 6.25 * height - 5 * age + 5
    else:  # female or other
        return 10 * weight + 6.25 * height - 5 * age - 161

def calculate_tdee(bmr: float, activity_level: str) -> float:
    """
    Calculate Total Daily Energy Expenditure (TDEE) based on activity level
    
    Multiply BMR by activity factor:
    - Sedentary (low): BMR × 1.2
    - Lightly active (moderate): BMR × 1.375
    - Moderately active (high): BMR × 1.55
    """
    activity_factors = {
        "low": 1.2,
        "moderate": 1.375,
        "high": 1.55
    }
    
    return bmr * activity_factors.get(activity_level, 1.2)

def calculate_calorie_target(tdee: float, goal: str, weight: float, desired_weight: float, goal_duration_weeks: int) -> float:
    """
    Calculate daily calorie target based on weight goal
    
    For weight loss or gain, we calculate the deficit/surplus needed to reach the goal:
    1 kg of fat = 7700 calories
    """
    if goal == "maintain":
        return tdee
    
    # Calculate weekly weight change needed
    total_weight_change = desired_weight - weight  # kg
    weekly_weight_change = total_weight_change / goal_duration_weeks  # kg per week
    
    # Calculate daily calorie adjustment
    # 7700 calories per kg, divided by 7 days
    daily_calorie_adjustment = (weekly_weight_change * 7700) / 7
    
    # For "lose" goal, daily_calorie_adjustment will be negative
    # For "gain" goal, daily_calorie_adjustment will be positive
    return tdee + daily_calorie_adjustment

def calculate_macros(calorie_target: float, diet_type: str) -> Dict[str, float]:
    """
    Calculate macro nutrient targets based on diet type
    Returns percentages of protein, fat, and carbs
    """
    # Default balanced diet
    macros = {
        "protein": 30,  # 30% of calories from protein
        "fat": 30,      # 30% of calories from fat
        "carb": 40,     # 40% of calories from carb
        "fiber": 25     # 25g of fiber (absolute value, not percentage)
    }
    
    if diet_type == "Vegeteria" or diet_type == "Vegan":
        # Higher carb, lower protein
        macros["protein"] = 20
        macros["fat"] = 30
        macros["carb"] = 50
        macros["fiber"] = 30
    
    elif diet_type == "Paleo":
        # Higher protein and fat, lower carb
        macros["protein"] = 35
        macros["fat"] = 40
        macros["carb"] = 25
        macros["fiber"] = 25
    
    elif diet_type == "Ketogenic":
        # Very high fat, very low carb
        macros["protein"] = 20
        macros["fat"] = 70
        macros["carb"] = 10
        macros["fiber"] = 20
    
    elif diet_type == "High protein":
        # Higher protein
        macros["protein"] = 40
        macros["fat"] = 30
        macros["carb"] = 30
        macros["fiber"] = 25
    
    elif diet_type == "Low carb":
        # Lower carb, higher fat
        macros["protein"] = 35
        macros["fat"] = 45
        macros["carb"] = 20
        macros["fiber"] = 20
    
    return macros

def calculate_nutrition_targets(profile: Dict[str, Any]) -> NutritionTargetCreate:
    """
    Calculate nutrition targets based on user profile
    """
    # Calculate BMR
    bmr = calculate_bmr(
        gender=profile.get("gender"),
        weight=profile.get("weight"),
        height=profile.get("height"),
        age=profile.get("age")
    )
    
    # Calculate TDEE
    tdee = calculate_tdee(bmr, profile.get("activity_level"))
    
    # Calculate calorie target
    calorie_target = calculate_calorie_target(
        tdee=tdee,
        goal=profile.get("goal"),
        weight=profile.get("weight"),
        desired_weight=profile.get("desired_weight"),
        goal_duration_weeks=profile.get("goal_duration_weeks")
    )
    
    # Calculate macro targets
    macros = calculate_macros(calorie_target, profile.get("diet_type"))
    
    # Create nutrition target
    nutrition_target = NutritionTargetCreate(
        target_calories=calorie_target,
        target_protein=macros["protein"],
        target_fat=macros["fat"],
        target_carb=macros["carb"],
        target_fiber=macros["fiber"]
    )
    
    return nutrition_target

async def create_or_update_nutrition_target(user_id: str) -> Dict[str, Any]:
    """
    Create or update nutrition targets for a user based on their profile
    """
    # Get user profile
    profile = await profiles_collection.find_one({"user_id": user_id})
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
    
    # Calculate nutrition targets
    nutrition_target_data = calculate_nutrition_targets(profile)
    
    # Check if user already has a nutrition target
    existing_target = await nutrition_targets_collection.find_one({"user_id": user_id})
    
    if existing_target:
        # Update existing target
        await nutrition_targets_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "target_calories": nutrition_target_data.target_calories,
                "target_protein": nutrition_target_data.target_protein,
                "target_fat": nutrition_target_data.target_fat,
                "target_carb": nutrition_target_data.target_carb,
                "target_fiber": nutrition_target_data.target_fiber,
                "updated_at": datetime.utcnow()
            }}
        )
        # Get updated target
        updated_target = await nutrition_targets_collection.find_one({"user_id": user_id})
        updated_target["id"] = str(updated_target["_id"])
        return updated_target
    else:
        # Create new target
        new_target = {
            "user_id": user_id,
            "target_calories": nutrition_target_data.target_calories,
            "target_protein": nutrition_target_data.target_protein,
            "target_fat": nutrition_target_data.target_fat,
            "target_carb": nutrition_target_data.target_carb,
            "target_fiber": nutrition_target_data.target_fiber,
            "updated_at": datetime.utcnow()
        }
        # Insert into database
        result = await nutrition_targets_collection.insert_one(new_target)
        # Get created target
        created_target = await nutrition_targets_collection.find_one({"_id": result.inserted_id})
        created_target["id"] = str(created_target["_id"])
        return created_target

def calculate_nutrition_score(actual_nutrition: Dict[str, float], target_nutrition: Dict[str, float]) -> int:
    """
    Calculate a nutrition score on a 100-point scale based on how well the actual nutrition
    matches the target nutrition values.
    
    Score breakdown:
    - Calories: 30 points (matching target calories within ±10%)
    - Macronutrient balance: 50 points (protein, fat, carbs matching target percentages)
    - Fiber: 20 points (meeting fiber target)
    
    Returns:
        int: Score from 0 to 100, where 100 is perfect adherence to targets
    """
    score = 0
    
    # Calculate calorie score (30 points)
    # Full points if within ±10% of target, decreasing linearly for larger deviations
    # (up to ±30% deviation, beyond which score is 0)
    target_calories = target_nutrition.get("target_calories", 2000)
    actual_calories = actual_nutrition.get("calories", 0)
    
    calorie_deviation_percent = abs(actual_calories - target_calories) / target_calories * 100
    if calorie_deviation_percent <= 10:
        calorie_score = 30  # Full points for ≤10% deviation
    elif calorie_deviation_percent <= 30:
        # Linear decrease from 30 points at 10% deviation to 0 points at 30% deviation
        calorie_score = 30 * (1 - (calorie_deviation_percent - 10) / 20)
    else:
        calorie_score = 0
    
    score += calorie_score
    
    # Calculate macronutrient balance score (50 points)
    # Each macro (protein, fat, carbs) is worth up to 16-17 points
    macro_nutrients = ["protein", "fat", "carb"]
    target_macros = {
        "protein": target_nutrition.get("target_protein", 30),
        "fat": target_nutrition.get("target_fat", 30),
        "carb": target_nutrition.get("target_carb", 40)
    }
    
    actual_macros = {
        "protein": actual_nutrition.get("protein", 0),
        "fat": actual_nutrition.get("fat", 0),
        "carb": actual_nutrition.get("carb", 0)
    }
    
    # Calculate total actual calories from macros
    actual_total_calories = actual_nutrition.get("calories", 0)
    
    # Convert actual grams to percentages
    if actual_total_calories > 0:
        # Protein: 4 calories per gram
        actual_protein_pct = (actual_macros["protein"] * 4 / actual_total_calories) * 100
        # Fat: 9 calories per gram
        actual_fat_pct = (actual_macros["fat"] * 9 / actual_total_calories) * 100
        # Carbs: 4 calories per gram
        actual_carb_pct = (actual_macros["carb"] * 4 / actual_total_calories) * 100
    else:
        actual_protein_pct = 0
        actual_fat_pct = 0
        actual_carb_pct = 0
    
    actual_macro_pcts = {
        "protein": actual_protein_pct,
        "fat": actual_fat_pct,
        "carb": actual_carb_pct
    }
    
    macro_score = 0
    for macro in macro_nutrients:
        target_pct = target_macros[macro]
        actual_pct = actual_macro_pcts[macro]
        
        # Calculate deviation (percentage points)
        deviation = abs(actual_pct - target_pct)
        
        # Award points based on closeness to target percentage
        # Full points if within 5 percentage points, decreasing linearly to 0 points at 20+ percentage points
        if deviation <= 5:
            macro_points = 16.67  # Full points (50/3)
        elif deviation <= 20:
            macro_points = 16.67 * (1 - (deviation - 5) / 15)
        else:
            macro_points = 0
        
        macro_score += macro_points
    
    score += macro_score
    
    # Calculate fiber score (20 points)
    # Full points if meeting or exceeding target, decreasing linearly to 0 points for 50% of target
    target_fiber = target_nutrition.get("target_fiber", 25)
    actual_fiber = actual_nutrition.get("fiber", 0)
    
    fiber_percent = (actual_fiber / target_fiber) * 100 if target_fiber > 0 else 0
    
    if fiber_percent >= 100:
        fiber_score = 20  # Full points for meeting or exceeding target
    elif fiber_percent >= 50:
        # Linear decrease from 20 points at 100% to 0 points at 50%
        fiber_score = 20 * ((fiber_percent - 50) / 50)
    else:
        fiber_score = 0
    
    score += fiber_score
    
    # Round to nearest integer and ensure score is between 0 and 100
    return max(0, min(100, round(score)))

async def evaluate_nutrition(
    actual_nutrition: Dict[str, float], 
    user_id: str
) -> Dict[str, Any]:
    """
    Evaluate actual nutrition against user targets and calculate nutrition score
    
    Args:
        actual_nutrition: Dictionary with actual nutrition values (calories, protein, etc.)
        user_id: User ID to retrieve targets
        
    Returns:
        Dictionary with nutrition evaluation results including score and comparisons
    """
    # Get user's nutrition targets
    target = await nutrition_targets_collection.find_one({"user_id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="Nutrition target not found")
    
    # Create target nutrition dictionary
    target_nutrition = {
        "target_calories": target["target_calories"],
        "target_protein": target["target_protein"],
        "target_fat": target["target_fat"],
        "target_carb": target["target_carb"],
        "target_fiber": target["target_fiber"]
    }
    
    # Calculate nutrition score
    nutrition_score = calculate_nutrition_score(actual_nutrition, target_nutrition)
    
    # Calculate percentage differences for each nutrient
    calorie_diff_pct = ((actual_nutrition.get("calories", 0) - target["target_calories"]) / target["target_calories"]) * 100 if target["target_calories"] > 0 else 0
    
    # Convert actual grams to percentages for comparison
    total_calories = actual_nutrition.get("calories", 0)
    if total_calories > 0:
        actual_protein_pct = (actual_nutrition.get("protein", 0) * 4 / total_calories) * 100
        actual_fat_pct = (actual_nutrition.get("fat", 0) * 9 / total_calories) * 100
        actual_carb_pct = (actual_nutrition.get("carb", 0) * 4 / total_calories) * 100
    else:
        actual_protein_pct = 0
        actual_fat_pct = 0
        actual_carb_pct = 0
    
    protein_diff_pct = actual_protein_pct - target["target_protein"]
    fat_diff_pct = actual_fat_pct - target["target_fat"]
    carb_diff_pct = actual_carb_pct - target["target_carb"]
    fiber_diff_pct = ((actual_nutrition.get("fiber", 0) - target["target_fiber"]) / target["target_fiber"]) * 100 if target["target_fiber"] > 0 else 0
    
    # Create evaluation results
    evaluation = {
        "nutrition_score": nutrition_score,
        "comparisons": {
            "calories": {
                "actual": actual_nutrition.get("calories", 0),
                "target": target["target_calories"],
                "difference_percent": round(calorie_diff_pct, 1)
            },
            "protein": {
                "actual_percent": round(actual_protein_pct, 1),
                "target_percent": target["target_protein"],
                "difference_percent": round(protein_diff_pct, 1)
            },
            "fat": {
                "actual_percent": round(actual_fat_pct, 1),
                "target_percent": target["target_fat"],
                "difference_percent": round(fat_diff_pct, 1)
            },
            "carb": {
                "actual_percent": round(actual_carb_pct, 1),
                "target_percent": target["target_carb"],
                "difference_percent": round(carb_diff_pct, 1)
            },
            "fiber": {
                "actual": actual_nutrition.get("fiber", 0),
                "target": target["target_fiber"],
                "difference_percent": round(fiber_diff_pct, 1)
            }
        }
    }
    
    return evaluation