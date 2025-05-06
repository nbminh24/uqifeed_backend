from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
from src.config.database import PyObjectId
from src.schemas.food.food_schema import MealTypeEnum, FoodIngredientBase

# Base schema cho các dish model
class DishBase(BaseModel):
    """Base schema for dishes"""
    name: str
    meal_type: MealTypeEnum
    description: Optional[str] = None
    eating_time: datetime
    image_url: Optional[str] = None

class DishCreate(DishBase):
    """Schema for creating a new dish"""
    user_id: str
    ingredients: List[FoodIngredientBase]

class DishResponse(DishBase):
    """Schema for dish response"""
    id: str
    user_id: str
    ingredients: List[Dict]
    total_calories: float
    total_protein: float
    total_fat: float
    total_carb: float
    total_fiber: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class DishUpdate(BaseModel):
    """Schema for updating a dish - all fields optional"""
    name: Optional[str] = None
    meal_type: Optional[MealTypeEnum] = None
    description: Optional[str] = None
    eating_time: Optional[datetime] = None
    image_url: Optional[str] = None
    ingredients: Optional[List[FoodIngredientBase]] = None

# Schema cho request dish recognition
class DishRequest(BaseModel):
    """Schema for dish recognition request"""
    user_id: str
    image_url: str
    food_data: Optional[Dict] = None