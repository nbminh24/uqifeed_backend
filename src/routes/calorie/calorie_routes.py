from fastapi import APIRouter, Depends, HTTPException, Body, Query
from typing import List, Dict, Optional
from datetime import datetime, date
from pydantic import BaseModel

from src.services.calorie import (
    calculate_dish_calories,
    create_nutrition_comparison,
    calculate_nutrition_score,
    generate_strengths,
    generate_weaknesses,
    generate_nutrient_comment,
    update_daily_report,
    generate_weekly_report,
    get_weekly_statistics,
    calculate_meal_calories,
    calculate_total_nutrition
)
from src.middleware import get_current_user

router = APIRouter()

class CaloriesRequest(BaseModel):
    food_id: str

class DateRequest(BaseModel):
    date: str  # Format: YYYY-MM-DD

class WeekRequest(BaseModel):
    week_start_date: str  # Format: YYYY-MM-DD

class MealRequest(BaseModel):
    date: str  # Format: YYYY-MM-DD
    meal_type: str  # breakfast, lunch, dinner, snack

@router.post("/dish-calories")
async def dish_calories_endpoint(
    request: CaloriesRequest,
    current_user: dict = Depends(get_current_user)
):
    """Calculate caloric content of a dish"""
    return await calculate_dish_calories(request.food_id, current_user["id"])

@router.post("/comparison")
async def create_comparison_endpoint(
    request: CaloriesRequest, 
    current_user: dict = Depends(get_current_user)
):
    """Create a nutrition comparison between food and user's target"""
    comparison = await create_nutrition_comparison(request.food_id, current_user["id"])
    
    # Enhance the comparison with analysis
    comparison["nutrition_score"] = await calculate_nutrition_score(comparison)
    comparison["strengths"] = await generate_strengths(comparison)
    comparison["weaknesses"] = await generate_weaknesses(comparison)
    
    # Add specific nutrient comments
    comparison["calories_comment"] = await generate_nutrient_comment(
        comparison, "diff_calories", "calorie"
    )
    comparison["protein_comment"] = await generate_nutrient_comment(
        comparison, "diff_protein", "protein"
    )
    comparison["fat_comment"] = await generate_nutrient_comment(
        comparison, "diff_fat", "fat"
    )
    comparison["carb_comment"] = await generate_nutrient_comment(
        comparison, "diff_carb", "carbohydrate"
    )
    comparison["fiber_comment"] = await generate_nutrient_comment(
        comparison, "diff_fiber", "fiber"
    )
    
    return comparison

@router.post("/daily-report")
async def daily_report_endpoint(
    request: DateRequest,
    current_user: dict = Depends(get_current_user)
):
    """Get or update daily nutrition report"""
    try:
        date_obj = datetime.strptime(request.date, "%Y-%m-%d").date()
        return await update_daily_report(current_user["id"], date_obj)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

@router.post("/weekly-report")
async def weekly_report_endpoint(
    request: WeekRequest,
    current_user: dict = Depends(get_current_user)
):
    """Generate weekly nutrition report"""
    try:
        start_date = datetime.strptime(request.week_start_date, "%Y-%m-%d").date()
        return await generate_weekly_report(current_user["id"], start_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

@router.post("/weekly-statistics")
async def weekly_statistics_endpoint(
    request: Optional[WeekRequest] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get weekly statistics for visualization"""
    try:
        start_date = None
        if request and request.week_start_date:
            start_date = datetime.strptime(request.week_start_date, "%Y-%m-%d").date()
            
        return await get_weekly_statistics(current_user["id"], start_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

@router.post("/meal-calories")
async def meal_calories_endpoint(
    request: MealRequest,
    current_user: dict = Depends(get_current_user)
):
    """Calculate calories for a specific meal on a specific date"""
    return await calculate_meal_calories(
        current_user["id"], 
        request.date, 
        request.meal_type
    )

@router.post("/daily-nutrition")
async def daily_nutrition_endpoint(
    request: Optional[DateRequest] = None,
    current_user: dict = Depends(get_current_user)
):
    """Calculate total nutrition for a specific date"""
    date_str = None
    if request and request.date:
        date_str = request.date
        
    return await calculate_total_nutrition(current_user["id"], date_str)