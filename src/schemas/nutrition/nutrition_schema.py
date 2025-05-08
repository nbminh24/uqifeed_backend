from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date

class NutritionTarget(BaseModel):
    """Base nutrition target schema with common fields"""
    bmr: int  # Basal Metabolic Rate
    tdee: int  # Total Daily Energy Expenditure
    calories: int
    protein: int  # in grams
    carb: int  # in grams (đổi từ carbs sang carb để đồng nhất với database)
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

class SubstitutionItem(BaseModel):
    """Schema for food substitution recommendations"""
    original: str
    substitute: str
    benefit: str

class AdviseBase(BaseModel):
    """Schema for nutrition advice"""
    recommendations: List[str]
    substitutions: List[SubstitutionItem]
    tips: List[str]

class DailyReportBase(BaseModel):
    """Schema for daily nutrition reports"""
    report_date: date
    total_calories: float
    total_protein: float
    total_fat: float
    total_carb: float
    total_fiber: float
    avg_nutrition_score: Optional[float] = 0

class WeeklyReportBase(BaseModel):
    """Schema for weekly nutrition reports"""
    week_start_date: date
    week_end_date: date
    avg_calories: float
    avg_protein: float
    avg_fat: float
    avg_carb: float
    avg_fiber: float
    avg_nutrition_score: Optional[float] = 0

class WeeklyIngredientUsageBase(BaseModel):
    """Schema for weekly ingredient usage statistics"""
    ingredient_id: str
    usage_count: int
    total_quantity: float