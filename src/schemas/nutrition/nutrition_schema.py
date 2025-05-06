from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class NutritionTarget(BaseModel):
    """Base nutrition target schema with common fields"""
    bmr: int  # Basal Metabolic Rate
    tdee: int  # Total Daily Energy Expenditure
    calories: int
    protein: int  # in grams
    carbs: int  # in grams
    fat: int  # in grams
    fiber: int  # in grams
    water: int  # in milliliters

class NutritionTargetResponse(NutritionTarget):
    """Schema for nutrition target response"""
    id: str
    user_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class WeeklyProjection(BaseModel):
    """Schema for weekly weight projection"""
    week: int
    weight: float

class ProgressProjection(BaseModel):
    """Schema for weight progress projection"""
    start_weight: float
    desired_weight: float
    goal_duration_weeks: int
    weekly_change: float
    weekly_projections: List[Dict[str, Any]]