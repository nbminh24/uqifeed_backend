from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"

class ActivityLevel(str, Enum):
    SEDENTARY = "SEDENTARY"
    LIGHTLY_ACTIVE = "LIGHTLY_ACTIVE"
    MODERATELY_ACTIVE = "MODERATELY_ACTIVE"
    VERY_ACTIVE = "VERY_ACTIVE"
    EXTRA_ACTIVE = "EXTRA_ACTIVE"

class WeightGoal(str, Enum):
    LOSE = "LOSE"
    MAINTAIN = "MAINTAIN"
    GAIN = "GAIN"

class DietType(str, Enum):
    STANDARD = "STANDARD"
    HIGH_PROTEIN = "HIGH_PROTEIN"
    KETO = "KETO"
    LOW_FAT = "LOW_FAT"
    VEGETARIAN = "VEGETARIAN"
    VEGAN = "VEGAN"
    MEDITERRANEAN = "MEDITERRANEAN"

class AdditionalGoal(str, Enum):
    MUSCLE_GAIN = "MUSCLE_GAIN"
    IMPROVED_FITNESS = "IMPROVED_FITNESS"
    BETTER_SLEEP = "BETTER_SLEEP"
    INCREASED_ENERGY = "INCREASED_ENERGY"
    REDUCED_STRESS = "REDUCED_STRESS"
    IMPROVED_DIGESTION = "IMPROVED_DIGESTION"
    BALANCED_NUTRITION = "BALANCED_NUTRITION"
    BETTER_HYDRATION = "BETTER_HYDRATION"
    REDUCED_SUGAR = "REDUCED_SUGAR"
    HEART_HEALTH = "HEART_HEALTH"

class ProfileBase(BaseModel):
    """Base profile schema with common fields"""
    gender: Gender
    birthdate: date
    height: float  # in cm
    weight: float  # in kg
    activity_level: ActivityLevel
    goal: WeightGoal
    diet_type: DietType

class ProfileNutritionCreate(ProfileBase):
    """Schema for creating a complete profile"""
    desired_weight: Optional[float] = None
    goal_duration_weeks: Optional[int] = None
    additional_goals: Optional[List[AdditionalGoal]] = []

class ProfileNutritionUpdate(BaseModel):
    """Schema for updating a profile - all fields optional"""
    gender: Optional[Gender] = None
    birthdate: Optional[date] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    desired_weight: Optional[float] = None
    goal_duration_weeks: Optional[int] = None
    activity_level: Optional[ActivityLevel] = None
    goal: Optional[WeightGoal] = None
    diet_type: Optional[DietType] = None
    additional_goals: Optional[List[AdditionalGoal]] = None

class ProfileNutritionResponse(BaseModel):
    """Schema for profile response - used when returning profile data"""
    id: str
    user_id: str
    gender: Gender
    birthdate: date
    height: float
    weight: float
    desired_weight: Optional[float] = None
    goal_duration_weeks: Optional[int] = None
    activity_level: ActivityLevel
    goal: WeightGoal
    diet_type: DietType
    additional_goals: Optional[List[AdditionalGoal]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True