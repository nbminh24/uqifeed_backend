from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import date
from enum import Enum

class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

class WeightGoal(str, Enum):
    LOSE = "LOSE"
    MAINTAIN = "MAINTAIN"
    GAIN = "GAIN"

class ActivityLevel(str, Enum):
    SEDENTARY = "SEDENTARY"
    LIGHTLY_ACTIVE = "LIGHTLY_ACTIVE"
    MODERATELY_ACTIVE = "MODERATELY_ACTIVE"
    VERY_ACTIVE = "VERY_ACTIVE"
    EXTREMELY_ACTIVE = "EXTREMELY_ACTIVE"

class DietType(str, Enum):
    BALANCED = "BALANCED"
    VEGETARIAN = "VEGETARIAN"
    VEGAN = "VEGAN"
    PALEO = "PALEO"
    KETO = "KETO"
    HIGH_PROTEIN = "HIGH_PROTEIN"
    LOW_CARB = "LOW_CARB"

class AdditionalGoal(str, Enum):
    EAT_MORE_GREENS = "EAT_MORE_GREENS"
    DRINK_MORE_WATER = "DRINK_MORE_WATER"
    REDUCE_SUGAR_SALT = "REDUCE_SUGAR_SALT"
    INCREASE_FIBER = "INCREASE_FIBER"
    EAT_MORE_PROTEIN = "EAT_MORE_PROTEIN"
    EAT_FEWER_CARBS = "EAT_FEWER_CARBS"
    IMPROVE_HABITS = "IMPROVE_HABITS"

class ProfileValidation(BaseModel):
    gender: Gender
    birthdate: date
    height: float = Field(..., gt=0, lt=300)  # cm
    weight: float = Field(..., gt=0, lt=500)  # kg
    goal: WeightGoal
    activity_level: ActivityLevel
    diet_type: DietType
    desired_weight: Optional[float] = None
    goal_duration_weeks: Optional[int] = None
    additional_goals: List[AdditionalGoal] = []

    @validator('birthdate')
    def validate_age(cls, v):
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 13:
            raise ValueError('User must be at least 13 years old')
        if age > 100:
            raise ValueError('Invalid age')
        return v

    @validator('desired_weight')
    def validate_weight_goal(cls, v, values):
        if 'weight' in values and 'goal' in values:
            current_weight = values['weight']
            goal = values['goal']
            
            if goal in ['LOSE', 'GAIN']:
                if not v:
                    raise ValueError('Desired weight is required for weight loss/gain goals')
                
                weight_change = abs(v - current_weight)
                if weight_change > 100:  # kg
                    raise ValueError('Weight change goal is too extreme')
                
                if 'goal_duration_weeks' in values:
                    weeks = values['goal_duration_weeks']
                    weekly_change = weight_change / weeks
                    if weekly_change > 1.0:  # kg per week
                        raise ValueError('Weekly weight change is too aggressive')
        
        return v

    @validator('goal_duration_weeks')
    def validate_duration(cls, v, values):
        if 'goal' in values and values['goal'] in ['LOSE', 'GAIN']:
            if not v:
                raise ValueError('Goal duration is required for weight loss/gain goals')
            if v < 1 or v > 104:  # 2 years max
                raise ValueError('Goal duration must be between 1 and 104 weeks')
        return v 