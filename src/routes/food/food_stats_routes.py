from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
from typing import List, Dict, Any
from src.services.authentication.user_auth import get_current_user
from src.services.food.food_stats_service import FoodStatsService
from src.utils.error_handler import handle_error
from src.utils.rate_limiter import rate_limit

router = APIRouter()

@router.get("/weekly")
@handle_error
@rate_limit(max_requests=30, window_seconds=60)
async def get_weekly_stats(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get weekly food consumption statistics
    """
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Get stats service
    stats_service = FoodStatsService(current_user["_id"])
    
    # Get daily stats
    daily_stats = await stats_service.get_daily_stats(start_date, end_date)
    
    # Calculate weekly totals
    weekly_totals = {
        "calories": sum(day["calories"] for day in daily_stats),
        "protein": sum(day["protein"] for day in daily_stats),
        "carbs": sum(day["carbs"] for day in daily_stats),
        "fat": sum(day["fat"] for day in daily_stats),
        "fiber": sum(day["fiber"] for day in daily_stats)
    }
    
    # Calculate weekly averages
    weekly_averages = {
        "calories": weekly_totals["calories"] / 7,
        "protein": weekly_totals["protein"] / 7,
        "carbs": weekly_totals["carbs"] / 7,
        "fat": weekly_totals["fat"] / 7,
        "fiber": weekly_totals["fiber"] / 7
    }
    
    # Get meal type distribution
    meal_distribution = await stats_service.get_meal_distribution(start_date, end_date)
    
    # Get most consumed foods
    top_foods = await stats_service.get_top_foods(start_date, end_date, limit=5)
    
    # Get nutrition goals
    nutrition_goals = await stats_service.get_nutrition_goals()
    
    # Calculate goal achievement
    goal_achievement = {
        "calories": (weekly_averages["calories"] / nutrition_goals["calories"]) * 100 if nutrition_goals["calories"] > 0 else 0,
        "protein": (weekly_averages["protein"] / nutrition_goals["protein"]) * 100 if nutrition_goals["protein"] > 0 else 0,
        "carbs": (weekly_averages["carbs"] / nutrition_goals["carbs"]) * 100 if nutrition_goals["carbs"] > 0 else 0,
        "fat": (weekly_averages["fat"] / nutrition_goals["fat"]) * 100 if nutrition_goals["fat"] > 0 else 0,
        "fiber": (weekly_averages["fiber"] / nutrition_goals["fiber"]) * 100 if nutrition_goals["fiber"] > 0 else 0
    }
    
    return {
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat()
        },
        "daily_stats": daily_stats,
        "weekly_totals": weekly_totals,
        "weekly_averages": weekly_averages,
        "meal_distribution": meal_distribution,
        "top_foods": top_foods,
        "nutrition_goals": nutrition_goals,
        "goal_achievement": goal_achievement
    }

@router.get("/daily")
@handle_error
@rate_limit(max_requests=30, window_seconds=60)
async def get_daily_stats(
    date: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get daily food consumption statistics
    """
    try:
        target_date = datetime.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    stats_service = FoodStatsService(current_user["_id"])
    return await stats_service.get_daily_stats(target_date, target_date) 