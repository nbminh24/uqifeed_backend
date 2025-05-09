from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
from bson import ObjectId
from fastapi import HTTPException
from functools import lru_cache

from src.config.database import (
    foods_collection, 
    nutrition_comparisons_collection, 
    nutrition_reviews_collection,
    advises_collection,
    nutrition_targets_collection,
    profiles_collection,
    progress_metrics_collection
)
from src.services.food.food_detector import detect_food_from_image
from src.config.constants import (
    CALORIE_DISTRIBUTION,
    MAX_CALORIES,
    MACRO_RATIOS,
    CACHE_SIZE,
    ERROR_MESSAGES
)
from src.utils.validation import validate_nutrition_values, validate_date_format
from src.utils.db_utils import safe_db_operation
from src.utils.websocket import websocket_manager

async def calculate_dish_calories(food_id: str, user_id: str) -> Dict:
    """
    Calculate caloric and nutritional values for a dish
    
    Args:
        food_id: The ID of the food item
        user_id: The ID of the user
        
    Returns:
        Dict with total nutritional values
    """
    try:
        # Get food details from database
        food = await foods_collection.find_one({"_id": ObjectId(food_id), "user_id": user_id})
        
        if not food:
            raise HTTPException(status_code=404, detail="Food not found")
        
        if not food.get("ingredients"):
            raise HTTPException(status_code=404, detail="No ingredients found for this food")

        total_protein = 0
        total_fat = 0
        total_carb = 0
        total_calories = 0

        # Calculate nutrients for each ingredient
        for ingredient in food["ingredients"]:
            protein = ingredient.get("protein", 0) * ingredient.get("quantity", 0) / 100
            fat = ingredient.get("fat", 0) * ingredient.get("quantity", 0) / 100
            carbs = ingredient.get("carb", 0) * ingredient.get("quantity", 0) / 100
            calories = (protein * 4) + (fat * 9) + (carbs * 4)

            # Sum up total nutrients
            total_protein += protein
            total_fat += fat
            total_carb += carbs
            total_calories += calories

        return {
            "food_id": food_id,
            "total_protein": total_protein,
            "total_fat": total_fat,
            "total_carb": total_carb,
            "total_calories": total_calories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating calories: {str(e)}")

async def create_nutrition_comparison(food_id: str, user_id: str) -> Dict:
    """
    Create a comparison between food and user's nutrition target
    
    Args:
        food_id: The ID of the food
        user_id: The ID of the user
        
    Returns:
        The created comparison
    """
    # Get food and target data
    food = await foods_collection.find_one({"_id": ObjectId(food_id)})
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    
    target = await nutrition_targets_collection.find_one({"user_id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="Nutrition target not found")
    
    # Calculate differences
    diff_calories = round((food.get("total_calories", 0) / target.get("calories", 1)) * 100)
    diff_protein = round((food.get("total_protein", 0) / target.get("protein", 1)) * 100)
    diff_fat = round((food.get("total_fat", 0) / target.get("fat", 1)) * 100)
    diff_carb = round((food.get("total_carb", 0) / target.get("carb", 1)) * 100)
    diff_fiber = round((food.get("total_fiber", 0) / target.get("fiber", 1)) * 100)
    
    # Create comparison document
    comparison = {
        "food_id": food_id,
        "target_id": str(target["_id"]),
        "user_id": user_id,
        "food_name": food.get("name", "Unknown Food"),
        "food_calories": food.get("total_calories", 0),
        "food_protein": food.get("total_protein", 0),
        "food_fat": food.get("total_fat", 0),
        "food_carb": food.get("total_carb", 0),
        "food_fiber": food.get("total_fiber", 0),
        "target_calories": target.get("calories", 0),
        "target_protein": target.get("protein", 0),
        "target_fat": target.get("fat", 0),
        "target_carb": target.get("carb", 0),
        "target_fiber": target.get("fiber", 0),
        "diff_calories": diff_calories,
        "diff_protein": diff_protein,
        "diff_fat": diff_fat,
        "diff_carb": diff_carb,
        "diff_fiber": diff_fiber,
        "created_at": datetime.utcnow()
    }
    
    # Insert into database
    result = await nutrition_comparisons_collection.insert_one(comparison)
    created_comparison = await nutrition_comparisons_collection.find_one({"_id": result.inserted_id})
    
    # Add id field for response
    created_comparison["id"] = str(created_comparison["_id"])
    
    return created_comparison

async def calculate_nutrition_score(comparison: Dict) -> int:
    """
    Calculate nutrition score based on target match
    
    Args:
        comparison: The nutrition comparison dict
        
    Returns:
        Score from 0-100
    """
    if not comparison:
        return 70  # Default score
    
    # Calculate deviation in each category
    calorie_dev = abs(comparison.get("diff_calories", 100) - 100)
    protein_dev = abs(comparison.get("diff_protein", 100) - 100)
    fat_dev = abs(comparison.get("diff_fat", 100) - 100)
    carb_dev = abs(comparison.get("diff_carb", 100) - 100)
    fiber_dev = abs(comparison.get("diff_fiber", 100) - 100)
    
    # Calculate weighted score 
    weighted_dev = (
        calorie_dev * 0.3 +
        protein_dev * 0.2 +
        fat_dev * 0.15 +
        carb_dev * 0.15 +
        fiber_dev * 0.2
    )
    
    # Convert to 0-100 score with a non-linear curve to be more forgiving
    score = max(0, min(100, round(100 - (weighted_dev / 2))))
    
    return score

async def generate_strengths(comparison: Dict) -> List[str]:
    """
    Generate nutritional strengths from a comparison
    
    Args:
        comparison: The nutrition comparison
        
    Returns:
        List of strength descriptions
    """
    strengths = []
    
    if not comparison:
        return ["Balanced nutrition"]
    
    # Check each nutrient
    if 90 <= comparison.get("diff_protein", 0) <= 120:
        strengths.append("Appropriate protein content")
    elif comparison.get("diff_protein", 0) > 120:
        strengths.append("High protein content")
    
    if 90 <= comparison.get("diff_fat", 0) <= 110:
        strengths.append("Well-balanced fat content")
    elif comparison.get("diff_fat", 0) < 90:
        strengths.append("Low fat content")
    
    if 90 <= comparison.get("diff_carb", 0) <= 110:
        strengths.append("Good carbohydrate balance")
    
    if comparison.get("diff_fiber", 0) >= 100:
        strengths.append("Good fiber content")
    
    if 90 <= comparison.get("diff_calories", 0) <= 110:
        strengths.append("Appropriate caloric content")
    elif comparison.get("diff_calories", 0) < 90:
        strengths.append("Low calorie option")
    
    # Ensure we have at least one strength
    if not strengths:
        strengths.append("Contributes to your daily nutrition")
    
    return strengths

async def generate_weaknesses(comparison: Dict) -> List[str]:
    """
    Generate nutritional weaknesses from a comparison
    
    Args:
        comparison: The nutrition comparison
        
    Returns:
        List of weakness descriptions
    """
    weaknesses = []
    
    if not comparison:
        return ["Minor deviations from targets"]
    
    # Check each nutrient
    if comparison.get("diff_protein", 0) < 70:
        weaknesses.append("Low protein content")
    elif comparison.get("diff_protein", 0) > 150:
        weaknesses.append("Excessive protein content")
    
    if comparison.get("diff_fat", 0) > 130:
        weaknesses.append("High fat content")
    
    if comparison.get("diff_carb", 0) > 130:
        weaknesses.append("High carbohydrate content")
    elif comparison.get("diff_carb", 0) < 70:
        weaknesses.append("Low carbohydrate content")
    
    if comparison.get("diff_fiber", 0) < 70:
        weaknesses.append("Low fiber content")
    
    if comparison.get("diff_calories", 0) > 130:
        weaknesses.append("High caloric content")
    
    # Ensure we don't have too many weaknesses
    if len(weaknesses) > 3:
        weaknesses = weaknesses[:3]
    
    # Ensure we have at least one item
    if not weaknesses:
        weaknesses.append("No significant nutritional concerns")
    
    return weaknesses

async def update_daily_report(user_id: str, report_date: Optional[date] = None) -> Dict:
    """
    Update or generate a daily nutrition report
    
    Args:
        user_id: The ID of the user
        report_date: The date for the report (default: today)
        
    Returns:
        The daily report
    """
    try:
        # Parse date or use today
        if not report_date:
            report_date = datetime.now().date()
            
        # Convert date to datetime range
        day_start = datetime.combine(report_date, datetime.min.time())
        day_end = datetime.combine(report_date, datetime.max.time())
        
        # Get all foods for the date
        foods = await foods_collection.find({
            "user_id": user_id,
            "eating_time": {"$gte": day_start, "$lte": day_end}
        }).to_list(length=100)
        
        # Calculate totals
        total_calories = sum(food.get("total_calories", 0) for food in foods)
        total_protein = sum(food.get("total_protein", 0) for food in foods)
        total_fat = sum(food.get("total_fat", 0) for food in foods)
        total_carb = sum(food.get("total_carb", 0) for food in foods)
        total_fiber = sum(food.get("total_fiber", 0) for food in foods)
        
        # Get target
        target = await nutrition_targets_collection.find_one({"user_id": user_id})
        
        # Calculate percentages
        calories_percent = 0
        protein_percent = 0
        fat_percent = 0
        carb_percent = 0
        fiber_percent = 0
        
        if target:
            calories_percent = round((total_calories / target.get("calories", 1)) * 100) if target.get("calories") else 0
            protein_percent = round((total_protein / target.get("protein", 1)) * 100) if target.get("protein") else 0
            fat_percent = round((total_fat / target.get("fat", 1)) * 100) if target.get("fat") else 0
            carb_percent = round((total_carb / target.get("carb", 1)) * 100) if target.get("carb") else 0
            fiber_percent = round((total_fiber / target.get("fiber", 1)) * 100) if target.get("fiber") else 0
        else:
            # If no target found, we can proceed without percentages
            pass
        
        # Build report
        report = {
            "date": report_date.isoformat(),
            "user_id": user_id,
            "total_calories": total_calories,
            "total_protein": total_protein,
            "total_fat": total_fat,
            "total_carb": total_carb,
            "total_fiber": total_fiber,
            "calories_percent": calories_percent,
            "protein_percent": protein_percent,
            "fat_percent": fat_percent,
            "carb_percent": carb_percent,
            "fiber_percent": fiber_percent,
            "meals": []
        }
        
        # Add target information if available
        if target:
            report["target_calories"] = target.get("calories", 0)
            report["target_protein"] = target.get("protein", 0)
            report["target_fat"] = target.get("fat", 0)
            report["target_carb"] = target.get("carb", 0)
            report["target_fiber"] = target.get("fiber", 0)
        
        # Group foods by meal type
        meal_types = {}
        for food in foods:
            meal_type = food.get("meal_type", "other")
            if meal_type not in meal_types:
                meal_types[meal_type] = []
            meal_types[meal_type].append(food)
        
        # Add meals data
        for meal_type, meal_foods in meal_types.items():
            report["meals"].append({
                "type": meal_type,
                "calories": sum(f.get("total_calories", 0) for f in meal_foods),
                "foods": [{"id": str(f["_id"]), "name": f.get("name", "Unknown Food")} for f in meal_foods]
            })
        
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating daily report: {str(e)}")

async def generate_weekly_report(user_id: str, week_start_date: date) -> Dict:
    """
    Generate a weekly nutrition report
    
    Args:
        user_id: The ID of the user
        week_start_date: The start date of the week
        
    Returns:
        The weekly report
    """
    # Initialize report
    report = {
        "week_start_date": week_start_date.isoformat(),
        "week_end_date": (week_start_date + timedelta(days=6)).isoformat(),
        "user_id": user_id,
        "daily_reports": [],
        "total_calories": 0,
        "total_protein": 0,
        "total_fat": 0,
        "total_carb": 0,
        "total_fiber": 0,
        "avg_calories": 0,
        "avg_protein": 0,
        "avg_fat": 0,
        "avg_carb": 0,
        "avg_fiber": 0
    }
    
    # Get target
    target = await nutrition_targets_collection.find_one({"user_id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="Nutrition target not found")
    
    report["target_calories"] = target.get("calories", 0)
    report["target_protein"] = target.get("protein", 0)
    report["target_fat"] = target.get("fat", 0)
    report["target_carb"] = target.get("carb", 0)
    report["target_fiber"] = target.get("fiber", 0)
    
    # Generate daily reports
    for day_offset in range(7):
        report_date = week_start_date + timedelta(days=day_offset)
        daily_report = await update_daily_report(user_id, report_date)
        
        report["daily_reports"].append(daily_report)
        
        # Add to weekly totals
        report["total_calories"] += daily_report["total_calories"]
        report["total_protein"] += daily_report["total_protein"]
        report["total_fat"] += daily_report["total_fat"]
        report["total_carb"] += daily_report["total_carb"]
        report["total_fiber"] += daily_report["total_fiber"]
    
    # Calculate averages
    report["avg_calories"] = report["total_calories"] / 7
    report["avg_protein"] = report["total_protein"] / 7
    report["avg_fat"] = report["total_fat"] / 7
    report["avg_carb"] = report["total_carb"] / 7
    report["avg_fiber"] = report["total_fiber"] / 7
    
    # Calculate percentages
    report["calories_percent"] = round((report["avg_calories"] / target.get("calories", 1)) * 100) if target.get("calories") else 0
    report["protein_percent"] = round((report["avg_protein"] / target.get("protein", 1)) * 100) if target.get("protein") else 0
    report["fat_percent"] = round((report["avg_fat"] / target.get("fat", 1)) * 100) if target.get("fat") else 0
    report["carb_percent"] = round((report["avg_carb"] / target.get("carb", 1)) * 100) if target.get("carb") else 0
    report["fiber_percent"] = round((report["avg_fiber"] / target.get("fiber", 1)) * 100) if target.get("fiber") else 0
    
    return report

async def get_weekly_statistics(
    user_id: str, 
    week_start_date: Optional[date] = None
) -> Dict:
    """
    Get comprehensive weekly statistics for visualization
    
    Args:
        user_id: The ID of the user
        week_start_date: Start date of the week (default: current week)
        
    Returns:
        Weekly statistics
    """
    try:
        # Use provided start date or calculate start of current week
        if not week_start_date:
            today = datetime.now().date()
            week_start_date = today - timedelta(days=today.weekday())
        
        # Calculate end date (Sunday)
        end_date = week_start_date + timedelta(days=6)
        
        # Get user profile for BMI calculation
        profile = await profiles_collection.find_one({"user_id": user_id})
        if not profile:
            raise HTTPException(status_code=404, detail="User profile not found")
        
        # Get nutrition target
        target = await nutrition_targets_collection.find_one({"user_id": user_id})
        if not target:
            raise HTTPException(status_code=404, detail="Nutrition target not found")
        
        # Initialize data structures for weekly tracking
        dates = []
        daily_scores = []
        daily_calories = []
        daily_protein = []
        daily_fat = []
        daily_carb = []
        daily_fiber = []
        
        # Initialize ingredient counter for food diversity
        from collections import Counter
        ingredient_counter = Counter()
        ingredient_details = {}
        
        # Generate dates for the week
        current_date = week_start_date
        while current_date <= end_date:
            dates.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=1)
        
        # Process each day of the week
        for day_offset in range(7):
            day_date = week_start_date + timedelta(days=day_offset)
            day_start = datetime.combine(day_date, datetime.min.time())
            day_end = datetime.combine(day_date, datetime.max.time())
            
            # Query foods for this day
            day_query = {
                "user_id": user_id,
                "eating_time": {"$gte": day_start, "$lte": day_end}
            }
            
            # Get all meals for the day
            day_foods = await foods_collection.find(day_query).to_list(length=100)
            
            # Calculate daily totals
            day_total_calories = 0
            day_total_protein = 0
            day_total_fat = 0
            day_total_carb = 0
            day_total_fiber = 0
            day_scores = []
            
            for food in day_foods:
                # Add nutrition values
                day_total_calories += food.get("total_calories", 0)
                day_total_protein += food.get("total_protein", 0)
                day_total_fat += food.get("total_fat", 0)
                day_total_carb += food.get("total_carb", 0)
                day_total_fiber += food.get("total_fiber", 0)
                
                # Add nutrition score if available
                if "nutrition_score" in food:
                    day_scores.append(food["nutrition_score"])
                
                # Process ingredients for food diversity
                if "ingredients" in food:
                    for ingredient in food["ingredients"]:
                        ingredient_name = ingredient.get("name", "Unknown")
                        ingredient_counter[ingredient_name] += 1
                        
                        # Store ingredient details for later use
                        ingredient_id = str(ingredient.get("_id", ""))
                        if ingredient_id and ingredient_id not in ingredient_details:
                            ingredient_details[ingredient_id] = {
                                "name": ingredient_name,
                                "protein": ingredient.get("protein", 0),
                                "fat": ingredient.get("fat", 0),
                                "carb": ingredient.get("carb", 0),
                                "fiber": ingredient.get("fiber", 0)
                            }
            
            # Calculate average score for the day
            day_avg_score = sum(day_scores) / len(day_scores) if day_scores else 0
            
            # Add data to weekly tracking
            daily_calories.append(day_total_calories)
            daily_protein.append(day_total_protein)
            daily_fat.append(day_total_fat)
            daily_carb.append(day_total_carb)
            daily_fiber.append(day_total_fiber)
            daily_scores.append(round(day_avg_score))
        
        # Calculate weekly averages
        weekly_avg_calories = sum(daily_calories) / 7 if sum(daily_calories) > 0 else 0
        weekly_avg_protein = sum(daily_protein) / 7 if sum(daily_protein) > 0 else 0
        weekly_avg_fat = sum(daily_fat) / 7 if sum(daily_fat) > 0 else 0
        weekly_avg_carb = sum(daily_carb) / 7 if sum(daily_carb) > 0 else 0
        weekly_avg_fiber = sum(daily_fiber) / 7 if sum(daily_fiber) > 0 else 0
        weekly_avg_score = sum(daily_scores) / 7 if sum(daily_scores) > 0 else 0
        
        # Calculate BMI
        height_m = profile.get("height", 170) / 100  # Convert cm to m
        weight = profile.get("weight", 70)
        bmi = round(weight / (height_m * height_m), 1)
        
        # Get food diversity information
        most_common_ingredients = ingredient_counter.most_common(50)  # Get top 50 ingredients
        
        food_diversity = []
        for ingredient_name, count in most_common_ingredients:
            food_diversity.append({
                "name": ingredient_name,
                "count": count,
            })
        
        # Calculate deviations from target
        calories_deviation = round(((weekly_avg_calories / target.get("calories", 1)) - 1) * 100) if target.get("calories") else 0
        protein_deviation = round(((weekly_avg_protein / target.get("protein", 1)) - 1) * 100) if target.get("protein") else 0
        fat_deviation = round(((weekly_avg_fat / target.get("fat", 1)) - 1) * 100) if target.get("fat") else 0
        carb_deviation = round(((weekly_avg_carb / target.get("carb", 1)) - 1) * 100) if target.get("carb") else 0
        fiber_deviation = round(((weekly_avg_fiber / target.get("fiber", 1)) - 1) * 100) if target.get("fiber") else 0
        
        # Tạo đánh giá dinh dưỡng cho báo cáo tuần
        weekly_meal_data = {
            "meal_type": "weekly",
            "total_calories": weekly_avg_calories,
            "total_protein": weekly_avg_protein,
            "total_fat": weekly_avg_fat,
            "total_carb": weekly_avg_carb,
            "total_fiber": weekly_avg_fiber
        }
        
        # Đánh giá dinh dưỡng của tuần
        weekly_evaluation = await evaluate_meal_nutrition(weekly_meal_data, user_id)
        macro_reviews = {
            "calories": weekly_evaluation.get("calorie_comment", ""),
            "protein": weekly_evaluation.get("macro_evaluations", {}).get("protein", {}).get("comment", ""),
            "fat": weekly_evaluation.get("macro_evaluations", {}).get("fat", {}).get("comment", ""),
            "carb": weekly_evaluation.get("macro_evaluations", {}).get("carb", {}).get("comment", ""),
            "fiber": weekly_evaluation.get("macro_evaluations", {}).get("fiber", {}).get("comment", "")
        }
        
        return {
            "week_start_date": week_start_date,
            "week_end_date": end_date,
            "dates": dates,
            
            # BMI data
            "bmi": bmi,
            "bmi_category": await get_bmi_category(bmi),
            
            # Score chart data
            "nutrition_score": {
                "daily_scores": daily_scores,
                "average": round(weekly_avg_score),
                "max": max(daily_scores) if daily_scores else 0,
                "min": min(daily_scores) if daily_scores else 0,
            },
            
            # Macro charts data
            "calories": {
                "daily_values": daily_calories,
                "average": round(weekly_avg_calories),
                "target": target.get("calories", 2000),
                "deviation": calories_deviation,
                "review": macro_reviews["calories"],
            },
            "protein": {
                "daily_values": daily_protein,
                "average": round(weekly_avg_protein, 1),
                "target": target.get("protein", 60),
                "deviation": protein_deviation,
                "review": macro_reviews["protein"],
            },
            "fat": {
                "daily_values": daily_fat,
                "average": round(weekly_avg_fat, 1),
                "target": target.get("fat", 70),
                "deviation": fat_deviation,
                "review": macro_reviews["fat"],
            },
            "carb": {
                "daily_values": daily_carb,
                "average": round(weekly_avg_carb, 1),
                "target": target.get("carb", 300),
                "deviation": carb_deviation,
                "review": macro_reviews["carb"],
            },
            "fiber": {
                "daily_values": daily_fiber,
                "average": round(weekly_avg_fiber, 1),
                "target": target.get("fiber", 25),
                "deviation": fiber_deviation,
                "review": macro_reviews["fiber"],
            },
            
            # Food diversity data
            "food_diversity": {
                "total_count": len(ingredient_counter),
                "ingredients": food_diversity
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating weekly statistics: {str(e)}")

async def get_bmi_category(bmi: float) -> str:
    """
    Return the BMI category for a given BMI value
    
    Args:
        bmi: BMI value
        
    Returns:
        BMI category description
    """
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal weight"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obesity"

@lru_cache(maxsize=CACHE_SIZE)
async def get_meal_type_standard(meal_type: str) -> Dict[str, Any]:
    """
    Get nutrition standard for a meal type
    
    Args:
        meal_type: Type of meal (breakfast, lunch, dinner, snack, light_meal, drinks)
        
    Returns:
        Nutrition standard for the meal type
    """
    if meal_type not in CALORIE_DISTRIBUTION:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid meal type: {meal_type}"
        )
    
    standard = {
        "meal_type": meal_type,
        "calories_percentage": CALORIE_DISTRIBUTION.get(meal_type, 0) * 100 if CALORIE_DISTRIBUTION.get(meal_type) else None,
        "macro_ratios": MACRO_RATIOS.get(meal_type, {"carbs": 0.4, "protein": 0.3, "fat": 0.3})
    }
    
    # Add calorie limits for specific meal types
    if meal_type in ["snack", "light_meal"]:
        standard["max_calories"] = MAX_CALORIES[meal_type]
    elif meal_type == "drinks":
        standard["max_calories_per_100ml"] = MAX_CALORIES["drinks_per_100ml"]
    
    return standard

async def calculate_meal_calories(user_id: str, date_str: str, meal_type: str) -> Dict[str, Any]:
    """
    Calculate calories for a specific meal on a specific date
    
    Args:
        user_id: The ID of the user
        date_str: Date string in YYYY-MM-DD format
        meal_type: Type of meal (breakfast, lunch, dinner, snack)
        
    Returns:
        Meal calorie information
    """
    try:
        # Validate date format
        is_valid, error_msg = validate_date_format(date_str)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Parse date
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Create datetime range for the day
        day_start = datetime.combine(date_obj, datetime.min.time())
        day_end = datetime.combine(date_obj, datetime.max.time())
        
        # Query foods for this meal
        query = {
            "user_id": user_id,
            "meal_type": meal_type,
            "eating_time": {"$gte": day_start, "$lte": day_end}
        }
        
        # Get meals
        meals = await safe_db_operation(
            foods_collection.find(query).to_list(length=100)
        )
        
        # Calculate totals
        total_calories = sum(meal.get("total_calories", 0) for meal in meals)
        total_protein = sum(meal.get("total_protein", 0) for meal in meals)
        total_fat = sum(meal.get("total_fat", 0) for meal in meals)
        total_carb = sum(meal.get("total_carb", 0) for meal in meals)
        total_fiber = sum(meal.get("total_fiber", 0) for meal in meals)
        
        # Validate totals
        is_valid, error_msg = validate_nutrition_values(
            total_calories, total_protein, total_fat, total_carb
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        return {
            "date": date_str,
            "meal_type": meal_type,
            "total_calories": total_calories,
            "total_protein": total_protein,
            "total_fat": total_fat,
            "total_carb": total_carb,
            "total_fiber": total_fiber,
            "foods": [
                {
                    "id": str(meal["_id"]),
                    "name": meal.get("name", "Unknown Food"),
                    "calories": meal.get("total_calories", 0)
                }
                for meal in meals
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=ERROR_MESSAGES["db_operation_failed"].format(error=str(e))
        )

async def evaluate_meal_nutrition(meal_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Đánh giá dinh dưỡng của bữa ăn dựa trên loại bữa ăn và tỷ lệ macro
    
    Args:
        meal_data: Dữ liệu bữa ăn
        user_id: ID của người dùng
        
    Returns:
        Đánh giá dinh dưỡng của bữa ăn
    """
    try:
        meal_type = meal_data.get("meal_type", "lunch")
        
        # Lấy mục tiêu dinh dưỡng của người dùng
        target = await nutrition_targets_collection.find_one({"user_id": user_id})
        if not target:
            raise HTTPException(status_code=404, detail="Không tìm thấy mục tiêu dinh dưỡng")
            
        daily_calories = target.get("calories", 2000)
        
        # Lấy tiêu chuẩn dinh dưỡng cho loại bữa ăn
        meal_standard = await get_meal_type_standard(meal_type)
        
        # Tỷ lệ macro trong mỗi bữa ăn
        target_ratios = meal_standard["macro_ratios"]
        
        # Tính toán calo mục tiêu cho bữa ăn
        target_meal_calories = 0
        if meal_standard.get("calories_percentage"):
            target_meal_calories = daily_calories * (meal_standard["calories_percentage"] / 100)
        elif meal_type == "drinks":
            volume_ml = meal_data.get("volume_ml", 100)
            target_meal_calories = meal_standard.get("max_calories_per_100ml", 20) * (volume_ml / 100)
        elif "max_calories" in meal_standard:
            target_meal_calories = meal_standard["max_calories"]
        else:
            target_meal_calories = 200  # Mặc định cho các loại bữa ăn khác
        
        # Lấy thông tin dinh dưỡng thực tế của bữa ăn
        actual_calories = meal_data.get("total_calories", 0)
        actual_protein = meal_data.get("total_protein", 0)
        actual_fat = meal_data.get("total_fat", 0)
        actual_carb = meal_data.get("total_carb", 0)
        actual_fiber = meal_data.get("total_fiber", 0)
        
        # Tính tỷ lệ so với mục tiêu ngày
        daily_protein = target.get("protein", 60)
        daily_fat = target.get("fat", 70)
        daily_carb = target.get("carb", 300)
        daily_fiber = target.get("fiber", 25)
        
        # Tính tỷ lệ % so với mục tiêu hàng ngày cho từng chất dinh dưỡng
        protein_percentage = (actual_protein / daily_protein) * 100 if daily_protein > 0 else 0
        fat_percentage = (actual_fat / daily_fat) * 100 if daily_fat > 0 else 0
        carb_percentage = (actual_carb / daily_carb) * 100 if daily_carb > 0 else 0 
        fiber_percentage = (actual_fiber / daily_fiber) * 100 if daily_fiber > 0 else 0
        calorie_percentage = (actual_calories / daily_calories) * 100 if daily_calories > 0 else 0
        
        # Tính tổng năng lượng từ từng macronutrient
        protein_cals = actual_protein * 4  # 4 calories per gram protein
        fat_cals = actual_fat * 9          # 9 calories per gram fat
        carb_cals = actual_carb * 4        # 4 calories per gram carbs
        
        # Tính tỷ lệ phần trăm thực tế của các macronutrient
        total_macros_cals = protein_cals + fat_cals + carb_cals
        actual_protein_ratio = protein_cals / total_macros_cals if total_macros_cals > 0 else 0
        actual_fat_ratio = fat_cals / total_macros_cals if total_macros_cals > 0 else 0
        actual_carb_ratio = carb_cals / total_macros_cals if total_macros_cals > 0 else 0
        
        # Tính toán điểm và mức độ phù hợp với mục tiêu
        score = 100  # Điểm mặc định
        
        # Đánh giá calo
        calorie_ratio = actual_calories / target_meal_calories if target_meal_calories > 0 else 1
        calorie_evaluation = ""
        
        if meal_standard.get("calories_percentage"):  # Chỉ đánh giá calo cho các bữa chính
            if calorie_ratio < 0.8:
                calorie_evaluation = "Thấp hơn mục tiêu"
                score -= 15
            elif calorie_ratio > 1.2:
                calorie_evaluation = "Cao hơn mục tiêu"
                score -= 15
            else:
                calorie_evaluation = "Phù hợp với mục tiêu"
        else:  # Đánh giá calo cho bữa phụ
            if "max_calories" in meal_standard and actual_calories > meal_standard["max_calories"]:
                calorie_evaluation = f"Vượt quá giới hạn ({meal_standard['max_calories']} kcal)"
                score -= 15
            elif meal_type == "drinks" and "max_calories_per_100ml" in meal_standard:
                volume_ml = meal_data.get("volume_ml", 100)
                max_cals = meal_standard["max_calories_per_100ml"] * (volume_ml / 100)
                if actual_calories > max_cals:
                    calorie_evaluation = f"Vượt quá giới hạn cho đồ uống ({meal_standard['max_calories_per_100ml']} kcal/100ml)"
                    score -= 15
                else:
                    calorie_evaluation = "Phù hợp với giới hạn calo"
            else:
                calorie_evaluation = "Phù hợp với giới hạn calo"
                
        # Đánh giá các tỷ lệ macro
        macro_evaluations = {}
        
        # Tạo chi tiết nhận xét về từng chất dinh dưỡng - theo phong cách khoa học, ngắn gọn
        nutrient_comments = {
            "protein": {
                "balanced": "Lượng protein cân đối tốt cho nhu cầu cơ thể, hỗ trợ duy trì khối cơ và quá trình trao đổi chất.",
                "excessive": {
                    "high": "Lượng protein cao vượt nhu cầu. Lý tưởng cho tập luyện nặng, nhưng có thể gây áp lực lên thận nếu duy trì lâu dài.",
                    "moderate": "Protein hơi cao so với nhu cầu. Tốt cho phục hồi cơ bắp sau tập luyện, nhưng khó tối ưu nếu không hoạt động thể chất."
                },
                "deficient": {
                    "high": "Protein thấp hơn nhiều so với nhu cầu. Có thể dẫn đến mất cơ bắp và suy giảm chức năng miễn dịch. Cân nhắc bổ sung.",
                    "moderate": "Protein hơi thấp. Khó đạt hiệu quả tối ưu khi tập luyện và duy trì khối cơ. Nên bổ sung thêm."
                }
            },
            "fat": {
                "balanced": "Chất béo ở mức cân đối, hỗ trợ hấp thu vitamin, sản xuất hormone và cung cấp năng lượng dài hạn.",
                "excessive": {
                    "high": "Chất béo vượt mức đáng kể. Tăng nguy cơ tích tụ mỡ thừa và rối loạn lipid máu. Nên giảm khẩu phần.",
                    "moderate": "Chất béo hơi cao. Chú ý ưu tiên các nguồn béo không bão hòa từ cá, quả bơ và các loại hạt."
                },
                "deficient": {
                    "high": "Chất béo quá thấp, ảnh hưởng đến hấp thu vitamin tan trong dầu và sản xuất hormone. Cần bổ sung từ nguồn lành mạnh.",
                    "moderate": "Chất béo hơi thấp. Thêm dầu olive, hạt hoặc bơ đậu phộng để cải thiện hấp thu vitamin và hormone."
                }
            },
            "carbs": {
                "balanced": "Carb ở mức cân đối, cung cấp năng lượng tức thì và dự trữ glycogen cho hoạt động thể chất.",
                "excessive": {
                    "high": "Carb quá cao, dễ gây tăng đường huyết và tích trữ mỡ. Thích hợp nếu vận động mạnh, nếu không nên giảm khẩu phần.",
                    "moderate": "Carb hơi cao. Ưu tiên nguồn carb phức hợp có chỉ số đường huyết thấp để tối ưu năng lượng."
                },
                "deficient": {
                    "high": "Carb quá thấp, có thể dẫn đến thiếu năng lượng, mệt mỏi và khó tập trung. Nên bổ sung từ ngũ cốc nguyên hạt.",
                    "moderate": "Carb hơi thấp. Thêm trái cây, khoai lang hoặc ngũ cốc nguyên hạt để duy trì năng lượng tối ưu."
                }
            },
            "fiber": {
                "balanced": "Chất xơ ở mức lý tưởng, hỗ trợ tiêu hóa khỏe mạnh, ổn định đường huyết và tạo cảm giác no lâu.",
                "excessive": {
                    "high": "Chất xơ vượt mức khuyến nghị. Tốt cho đường ruột nhưng cần uống nhiều nước để tránh khó tiêu và đầy hơi.",
                    "moderate": "Chất xơ hơi cao. Đảm bảo uống đủ nước để tối ưu hiệu quả và tránh khó tiêu."
                },
                "deficient": {
                    "high": "Chất xơ quá thấp, tăng nguy cơ táo bón và mất cân bằng hệ vi sinh đường ruột. Cần bổ sung rau xanh và trái cây.",
                    "moderate": "Chất xơ hơi thấp. Thêm rau xanh, trái cây hoặc ngũ cốc nguyên hạt để cải thiện sức khỏe đường ruột."
                }
            },
            "calorie": {
                "balanced": "Calo cân đối với nhu cầu, hỗ trợ duy trì cân nặng hiện tại và cung cấp năng lượng tối ưu.",
                "excessive": {
                    "high": "Calo vượt mức đáng kể so với nhu cầu. Dẫn đến tích trữ mỡ thừa nếu không tăng hoạt động thể chất.",
                    "moderate": "Calo hơi cao so với nhu cầu. Phù hợp nếu tập luyện cường độ cao, nếu không nên giảm nhẹ khẩu phần."
                },
                "deficient": {
                    "high": "Calo quá thấp so với nhu cầu. Nguy cơ thiếu dinh dưỡng, giảm cơ và suy giảm chức năng trao đổi chất.",
                    "moderate": "Calo hơi thấp. Phù hợp nếu đang giảm cân, nếu không nên tăng khẩu phần để đáp ứng nhu cầu năng lượng."
                }
            }
        }
        
        if meal_type != "drinks":  # Không đánh giá tỷ lệ macro cho đồ uống
            # Đánh giá chi tiết cho từng macro và tạo nhận xét
            for macro, actual_ratio, macro_name, target_percent, daily_target, actual_value in [
                ("carbs", actual_carb_ratio, "Carbohydrate", carb_percentage, daily_carb, actual_carb),
                ("protein", actual_protein_ratio, "Protein", protein_percentage, daily_protein, actual_protein),
                ("fat", actual_fat_ratio, "Chất béo", fat_percentage, daily_fat, actual_fat)
            ]:
                # Đánh giá tỷ lệ trong bữa ăn
                target_ratio = target_ratios.get(macro, 0.33)
                ratio_diff = abs(actual_ratio - target_ratio)
                
                # Đánh giá tỉ lệ so với mục tiêu ngày
                nutrient_comment = ""
                if 90 <= target_percent <= 110:  # Cân đối
                    nutrient_comment = nutrient_comments[macro]["balanced"]
                elif target_percent > 110:  # Thừa
                    if target_percent > 150:  # Thừa nhiều
                        nutrient_comment = nutrient_comments[macro]["excessive"]["high"]
                    else:  # Thừa vừa phải
                        nutrient_comment = nutrient_comments[macro]["excessive"]["moderate"]
                else:  # Thiếu
                    if target_percent < 50:  # Thiếu nhiều
                        nutrient_comment = nutrient_comments[macro]["deficient"]["high"]
                    else:  # Thiếu vừa phải
                        nutrient_comment = nutrient_comments[macro]["deficient"]["moderate"]
                
                # Đánh giá cho tỷ lệ trong bữa ăn
                if ratio_diff < 0.05:  # Sai lệch dưới 5%
                    evaluation = "Cân đối tốt"
                elif ratio_diff < 0.1:  # Sai lệch dưới 10%
                    evaluation = "Gần như cân đối"
                    score -= 5
                else:
                    if actual_ratio > target_ratio:
                        evaluation = "Cao hơn khuyến nghị"
                    else:
                        evaluation = "Thấp hơn khuyến nghị"
                    score -= 10
                
                actual_percent = round(actual_ratio * 100)
                target_ratio_percent = round(target_ratio * 100)
                
                macro_evaluations[macro] = {
                    "name": macro_name,
                    "actual_value": round(actual_value, 1),
                    "daily_target": round(daily_target, 1),
                    "percentage_of_daily": round(target_percent),
                    "actual_ratio_percent": actual_percent,
                    "target_ratio_percent": target_ratio_percent,
                    "evaluation": evaluation,
                    "comment": nutrient_comment
                }
            
            # Thêm đánh giá cho chất xơ
            fiber_comment = ""
            if 90 <= fiber_percentage <= 110:  # Cân đối
                fiber_comment = nutrient_comments["fiber"]["balanced"]
            elif fiber_percentage > 110:  # Thừa
                if fiber_percentage > 150:  # Thừa nhiều
                    fiber_comment = nutrient_comments["fiber"]["excessive"]["high"]
                else:  # Thừa vừa phải
                    fiber_comment = nutrient_comments["fiber"]["excessive"]["moderate"]
            else:  # Thiếu
                if fiber_percentage < 50:  # Thiếu nhiều
                    fiber_comment = nutrient_comments["fiber"]["deficient"]["high"]
                else:  # Thiếu vừa phải
                    fiber_comment = nutrient_comments["fiber"]["deficient"]["moderate"]
                    
            # Đánh giá chất xơ trong bữa ăn
            if fiber_percentage < 70:
                score -= 10
                fiber_evaluation = "Thấp hơn khuyến nghị"
            elif fiber_percentage > 130:
                fiber_evaluation = "Cao hơn khuyến nghị"
            else:
                fiber_evaluation = "Cân đối tốt"
                
            macro_evaluations["fiber"] = {
                "name": "Chất xơ",
                "actual_value": round(actual_fiber, 1),
                "daily_target": round(daily_fiber, 1),
                "percentage_of_daily": round(fiber_percentage),
                "evaluation": fiber_evaluation,
                "comment": fiber_comment
            }
        
        # Đánh giá calo chi tiết
        calorie_comment = ""
        if 90 <= calorie_percentage <= 110:  # Cân đối
            calorie_comment = nutrient_comments["calorie"]["balanced"]
        elif calorie_percentage > 110:  # Thừa
            if calorie_percentage > 150:  # Thừa nhiều
                calorie_comment = nutrient_comments["calorie"]["excessive"]["high"]
            else:  # Thừa vừa phải
                calorie_comment = nutrient_comments["calorie"]["excessive"]["moderate"]
        else:  # Thiếu
            if calorie_percentage < 50:  # Thiếu nhiều
                calorie_comment = nutrient_comments["calorie"]["deficient"]["high"]
            else:  # Thiếu vừa phải
                calorie_comment = nutrient_comments["calorie"]["deficient"]["moderate"]
        
        # Đảm bảo điểm số nằm trong khoảng 0-100
        score = max(0, min(100, score))
        
        # Tạo danh sách điểm mạnh và điểm yếu từ hàm đánh giá
        strengths = await generate_strengths({
            "diff_protein": protein_percentage,
            "diff_fat": fat_percentage,
            "diff_carb": carb_percentage,
            "diff_fiber": fiber_percentage,
            "diff_calories": calorie_percentage
        })
        
        weaknesses = await generate_weaknesses({
            "diff_protein": protein_percentage,
            "diff_fat": fat_percentage,
            "diff_carb": carb_percentage,
            "diff_fiber": fiber_percentage,
            "diff_calories": calorie_percentage
        })
            
        return {
            "meal_type": meal_type,
            "actual_calories": round(actual_calories),
            "target_calories": round(target_meal_calories),
            "percentage_of_daily_calories": round(calorie_percentage),
            "calorie_ratio": round(calorie_ratio, 2),
            "calorie_evaluation": calorie_evaluation,
            "calorie_comment": calorie_comment,
            "macro_evaluations": macro_evaluations,
            "nutrition_score": round(score),
            "strengths": strengths,
            "weaknesses": weaknesses,
            "meal_standard_description": meal_standard["description"],
            "daily_targets": {
                "calories": round(daily_calories),
                "protein": round(daily_protein),
                "carbs": round(daily_carb),
                "fat": round(daily_fat),
                "fiber": round(daily_fiber)
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đánh giá dinh dưỡng bữa ăn: {str(e)}")

async def calculate_progress_metrics(user_id: str, current_date: date) -> Dict[str, Any]:
    """
    Calculate real-time progress metrics for the user
    
    Args:
        user_id: User ID
        current_date: Current date to calculate metrics for
        
    Returns:
        Dict containing progress metrics
    """
    try:
        # Get user profile and targets
        profile = await get_user_profile(user_id)
        targets = await get_nutrition_targets(user_id)
        
        if not profile or not targets:
            return None
            
        # Get daily nutrition data
        daily_data = await get_daily_nutrition(user_id, current_date)
        
        # Calculate progress metrics
        metrics = {
            "calories": {
                "current": daily_data.get("total_calories", 0),
                "target": targets.get("calories", 0),
                "percentage": min(100, (daily_data.get("total_calories", 0) / targets.get("calories", 1)) * 100)
            },
            "protein": {
                "current": daily_data.get("total_protein", 0),
                "target": targets.get("protein", 0),
                "percentage": min(100, (daily_data.get("total_protein", 0) / targets.get("protein", 1)) * 100)
            },
            "carbs": {
                "current": daily_data.get("total_carbs", 0),
                "target": targets.get("carbs", 0),
                "percentage": min(100, (daily_data.get("total_carbs", 0) / targets.get("carbs", 1)) * 100)
            },
            "fat": {
                "current": daily_data.get("total_fat", 0),
                "target": targets.get("fat", 0),
                "percentage": min(100, (daily_data.get("total_fat", 0) / targets.get("fat", 1)) * 100)
            },
            "fiber": {
                "current": daily_data.get("total_fiber", 0),
                "target": targets.get("fiber", 0),
                "percentage": min(100, (daily_data.get("total_fiber", 0) / targets.get("fiber", 1)) * 100)
            }
        }
        
        # Calculate overall progress
        overall_progress = sum(metric["percentage"] for metric in metrics.values()) / len(metrics)
        metrics["overall"] = {
            "percentage": overall_progress,
            "status": "on_track" if 90 <= overall_progress <= 110 else "needs_attention"
        }
        
        return metrics
        
    except Exception as e:
        logger.error(f"Error calculating progress metrics: {str(e)}")
        return None

async def update_progress_metrics(user_id: str, current_date: date) -> None:
    """
    Update progress metrics in real-time when nutrition data changes
    
    Args:
        user_id: User ID
        current_date: Current date to update metrics for
    """
    try:
        metrics = await calculate_progress_metrics(user_id, current_date)
        if metrics:
            # Update metrics in database
            await progress_metrics_collection.update_one(
                {
                    "user_id": user_id,
                    "date": current_date
                },
                {
                    "$set": {
                        "metrics": metrics,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            
            # Emit real-time update event
            await emit_progress_update(user_id, metrics)
            
    except Exception as e:
        logger.error(f"Error updating progress metrics: {str(e)}")

async def emit_progress_update(user_id: str, metrics: Dict[str, Any]) -> None:
    """
    Emit real-time progress update event
    
    Args:
        user_id: User ID
        metrics: Progress metrics to emit
    """
    try:
        # Emit WebSocket event for real-time updates
        await websocket_manager.broadcast_to_user(
            user_id,
            {
                "type": "progress_update",
                "data": metrics
            }
        )
    except Exception as e:
        logger.error(f"Error emitting progress update: {str(e)}")

async def calculate_nutrient_scores(food_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Calculate scores for each nutrient (protein, fiber, carbs, fat)
    
    Args:
        food_data: Food data containing nutrient values
        user_id: User ID for getting nutrition targets
        
    Returns:
        Dict containing scores for each nutrient
    """
    try:
        # Get user's nutrition targets
        target = await nutrition_targets_collection.find_one({"user_id": user_id})
        if not target:
            raise HTTPException(status_code=404, detail="Nutrition targets not found")
            
        # Calculate scores for each nutrient
        scores = {}
        for nutrient, target_key in [
            ("protein", "protein"),
            ("fiber", "fiber"),
            ("carb", "carb"),
            ("fat", "fat")
        ]:
            actual = food_data.get(f"total_{nutrient}", 0)
            target_value = target.get(target_key, 0)
            
            if target_value > 0:
                percentage = (actual / target_value) * 100
                # Score based on how close to target (100% is perfect)
                score = max(0, min(100, 100 - abs(percentage - 100)))
            else:
                score = 0
                
            scores[nutrient] = round(score)
            
        return scores
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating nutrient scores: {str(e)}")

async def generate_nutrition_badge(food_data: Dict[str, Any], user_id: str) -> str:
    """
    Generate a nutrition badge based on overall meal quality
    
    Args:
        food_data: Food data containing nutrient values
        user_id: User ID for getting nutrition targets
        
    Returns:
        String containing nutrition badge
    """
    try:
        # Get user's nutrition targets
        target = await nutrition_targets_collection.find_one({"user_id": user_id})
        if not target:
            raise HTTPException(status_code=404, detail="Nutrition targets not found")
            
        # Calculate overall score
        scores = await calculate_nutrient_scores(food_data, user_id)
        overall_score = sum(scores.values()) / len(scores)
        
        # Generate badge based on score
        if overall_score >= 90:
            return "Excellent Choice"
        elif overall_score >= 75:
            return "Great Balance"
        elif overall_score >= 60:
            return "Good Meal"
        else:
            return "Needs Improvement"
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating nutrition badge: {str(e)}")

