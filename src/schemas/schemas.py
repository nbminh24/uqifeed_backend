# Import các schema từ các module con để tránh trùng lặp
from src.schemas.user.user_schema import UserCreate, UserResponse
from src.schemas.food.food_schema import (
    MongoBaseModel,
    MealTypeEnum,
    FoodCategory,
    IngredientBase,
    IngredientCreate,
    IngredientResponse,
    FoodIngredientBase,
    FoodBase,
    FoodCreate,
    FoodUpdate,
    FoodResponse,
    DishBase,
    DishCreate,
    DishResponse,
    DishUpdate,
    FoodItem,
    FoodDetectionResponse,
    FoodImageUpload,
    IngredientRecognition,
    FoodRecognitionResponse,
    DishRequest,
    MealTypeNutritionalStandards,
    NutritionInfo
)
from src.schemas.notification.notification_schema import NotificationBase, ReminderTimes, NotificationSettingsBase
from src.schemas.nutrition.nutrition_schema import (
    NutritionTarget,
    NutritionTargetResponse,
    NutritionTargetBase,
    NutritionComparisonBase,
    NutritionReviewBase
)

from pydantic import BaseModel, EmailStr, Field, validator, root_validator
from typing import Optional, List, Union, Any, Dict
from datetime import datetime, date
from enum import Enum
from bson import ObjectId
from src.config.database import PyObjectId

# User Profile Enums
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

# User Profile Schemas
class ProfileNutritionCreate(BaseModel):
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
    updated_at: Optional[datetime] = None
    
    @validator('age', pre=True, always=True)
    def calculate_age(cls, v, values):
        if 'birthdate' in values:
            today = datetime.now().date()
            birthdate = values['birthdate']
            age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
            return age
        return v

# Progress Projection Schema
class ProgressProjection(BaseModel):
    start_date: date
    start_weight: float
    projected_dates: List[date]
    projected_weights: List[float]
    weekly_change_rate: float

# Measurement Unit schemas
class MeasurementUnitBase(BaseModel):
    name: str
    category: str  # weight, volume, quantity, etc.
    conversion_factor: float  # Factor to convert to base unit (e.g., grams)
    base_unit: str  # Base unit (e.g., "g" for grams)

# Weekly Ingredient Usage schemas
class WeeklyIngredientUsageBase(BaseModel):
    ingredient_id: str
    usage_count: int
    total_quantity: float

# Weekly Report Comment schemas
class ChartTypeEnum(str, Enum):
    CALORIES = "calories"
    PROTEIN = "protein"
    FAT = "fat"
    CARB = "carb"
    FIBER = "fiber"
    INGREDIENTS = "ingredients"

class WeeklyReportCommentBase(BaseModel):
    chart_type: ChartTypeEnum
    comment: str
    suggestions: str