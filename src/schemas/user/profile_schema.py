from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class ActivityLevel(str, Enum):
    SEDENTARY = "sedentary"
    LIGHTLY_ACTIVE = "lightly_active"
    MODERATELY_ACTIVE = "moderately_active"
    VERY_ACTIVE = "very_active"
    EXTREMELY_ACTIVE = "extremely_active"

class WeightGoal(str, Enum):
    LOSE = "lose"
    MAINTAIN = "maintain"
    GAIN = "gain"

class DietType(str, Enum):
    BALANCED = "balanced"
    VEGETARIAN = "vegetarian"
    VEGAN = "vegan"
    PALEO = "paleo"
    KETO = "keto"
    HIGH_PROTEIN = "high_protein"
    LOW_CARB = "low_carb"

class AdditionalGoal(str, Enum):
    EAT_MORE_GREENS = "eat_more_greens"
    DRINK_MORE_WATER = "drink_more_water"
    INCREASE_FIBER = "increase_fiber"
    EAT_LESS_SUGAR = "eat_less_sugar"
    REDUCE_SALT = "reduce_salt"
    EAT_MORE_PROTEIN = "eat_more_protein"
    IMPROVE_EATING_HABITS = "improve_eating_habits"
    EAT_FEWER_CARBS = "eat_fewer_carbs"

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

    @validator('height')
    def height_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Height must be positive')
        return v

    @validator('weight', 'desired_weight')
    def weight_must_be_positive(cls, v):
        if v and v <= 0:
            raise ValueError('Weight must be positive')
        return v

    @root_validator
    def check_desired_weight_required(cls, values):
        goal = values.get('goal')
        desired_weight = values.get('desired_weight')
        duration = values.get('goal_duration_weeks')
        
        if goal in [WeightGoal.LOSE, WeightGoal.GAIN]:
            if not desired_weight:
                raise ValueError('Desired weight is required when goal is to lose or gain weight')
            if not duration:
                raise ValueError('Goal duration is required when goal is to lose or gain weight')
        
        return values

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
    age: Optional[int] = None  # Calculated field
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
    
    @validator('age', pre=True, always=True)
    def calculate_age(cls, v, values):
        if 'birthdate' in values:
            today = datetime.now().date()
            birthdate = values['birthdate']
            age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
            return age
        return v
    
    class Config:
        orm_mode = True

# Progress Projection Schema
class ProgressProjection(BaseModel):
    """Schema for weight progress projection"""
    start_date: date
    start_weight: float
    projected_dates: List[date]
    projected_weights: List[float]
    weekly_change_rate: float