from pydantic import BaseModel, EmailStr, Field, root_validator
from typing import Optional, List, Union, Any
from datetime import datetime, date
from enum import Enum
from bson import ObjectId
from src.config.database import PyObjectId

# MongoDB ID schema
class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    name: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(MongoBaseModel, UserBase):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "id": "60d5ec9af3a7dadf2d73013d",
                "email": "user@example.com",
                "name": "User Name",
                "created_at": "2023-04-22T12:00:00"
            }
        }

# Profile schemas
class GenderEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"

class ActivityLevelEnum(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"

class GoalEnum(str, Enum):
    maintain = "maintain"
    lose = "lose"
    gain = "gain"

class DietTypeEnum(str, Enum):
    balanced = "Balanced"
    vegetarian = "Vegeteria"
    vegan = "Vegan"
    paleo = "Paleo"
    ketogenic = "Ketogenic"
    high_protein = "High protein"
    low_carb = "Low carb"

class ProfileNutritionBase(BaseModel):
    gender: GenderEnum
    age: int = Field(..., gt=0, lt=120)
    height: float = Field(..., gt=0)  # in cm
    weight: float = Field(..., gt=0)  # in kg
    desired_weight: float = Field(..., gt=0)  # in kg
    goal_duration_weeks: int = Field(..., gt=0)
    activity_level: ActivityLevelEnum
    goal: GoalEnum
    diet_type: DietTypeEnum

class ProfileNutritionCreate(ProfileNutritionBase):
    pass

class ProfileNutritionUpdate(BaseModel):
    gender: Optional[GenderEnum] = None
    age: Optional[int] = Field(None, gt=0, lt=120)
    height: Optional[float] = Field(None, gt=0)
    weight: Optional[float] = Field(None, gt=0)
    desired_weight: Optional[float] = Field(None, gt=0)
    goal_duration_weeks: Optional[int] = Field(None, gt=0)
    activity_level: Optional[ActivityLevelEnum] = None
    goal: Optional[GoalEnum] = None
    diet_type: Optional[DietTypeEnum] = None

class ProfileNutritionResponse(MongoBaseModel, ProfileNutritionBase):
    user_id: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Nutrition Target schemas
class NutritionTargetBase(BaseModel):
    target_calories: float = Field(..., gt=0)
    target_protein: float = Field(..., ge=0, le=100)  # percentage
    target_fat: float = Field(..., ge=0, le=100)  # percentage
    target_carb: float = Field(..., ge=0, le=100)  # percentage
    target_fiber: float = Field(..., ge=0)  # grams

    @root_validator(skip_on_failure=True)
    def check_percentages_sum_to_100(cls, values):
        protein = values.get('target_protein', 0)
        fat = values.get('target_fat', 0)
        carb = values.get('target_carb', 0)
        
        if abs(protein + fat + carb - 100) > 0.01:  # Allow small floating point errors
            raise ValueError("Protein, fat, and carb percentages must sum to 100%")
        
        return values

class NutritionTargetCreate(NutritionTargetBase):
    pass

class NutritionTargetUpdate(BaseModel):
    target_calories: Optional[float] = Field(None, gt=0)
    target_protein: Optional[float] = Field(None, ge=0, le=100)
    target_fat: Optional[float] = Field(None, ge=0, le=100)
    target_carb: Optional[float] = Field(None, ge=0, le=100)
    target_fiber: Optional[float] = Field(None, ge=0)

class NutritionTargetResponse(MongoBaseModel, NutritionTargetBase):
    user_id: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Ingredient schemas
class IngredientBase(BaseModel):
    name: str
    tip: Optional[str] = None
    unit: str
    protein: float = Field(..., ge=0)
    fat: float = Field(..., ge=0)
    carb: float = Field(..., ge=0)
    fiber: float = Field(..., ge=0)
    
    @root_validator(skip_on_failure=True)
    def calculate_calories(cls, values):
        protein = values.get('protein', 0)
        fat = values.get('fat', 0)
        carb = values.get('carb', 0)
        
        values['calories'] = 4 * protein + 9 * fat + 4 * carb
        return values

class IngredientCreate(IngredientBase):
    pass

class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    tip: Optional[str] = None
    unit: Optional[str] = None
    protein: Optional[float] = Field(None, ge=0)
    fat: Optional[float] = Field(None, ge=0)
    carb: Optional[float] = Field(None, ge=0)
    fiber: Optional[float] = Field(None, ge=0)

class IngredientResponse(MongoBaseModel, IngredientBase):
    calories: float

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Food schemas
class MealTypeEnum(str, Enum):
    breakfast = "breakfast"
    lunch = "lunch"
    dinner = "dinner"
    snack = "snack"
    drinks = "drinks"
    light_meal = "light_meal"

class FoodIngredientBase(BaseModel):
    ingredient_id: str
    quantity: float = Field(..., gt=0)

class FoodIngredientCreate(FoodIngredientBase):
    pass

class FoodIngredientResponse(FoodIngredientBase):
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class FoodBase(BaseModel):
    name: str
    meal_type: MealTypeEnum
    description: Optional[str] = None
    eating_time: datetime

class FoodCreate(FoodBase):
    ingredients: List[FoodIngredientCreate]
    image_url: Optional[str] = None

class FoodResponse(MongoBaseModel, FoodBase):
    user_id: str
    total_calories: float
    total_protein: float
    total_fat: float
    total_carb: float
    total_fiber: float
    image_url: Optional[str] = None
    nutrition_score: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ingredients: List[FoodIngredientResponse]

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Meal Type Nutritional Standards schema
class MealTypeNutritionalStandards(BaseModel):
    meal_type: MealTypeEnum
    calories_percentage: float = Field(..., ge=0, le=100)  # Percentage of daily target
    protein_percentage: float = Field(..., ge=0, le=100)  # Percentage of daily target
    fat_percentage: float = Field(..., ge=0, le=100)  # Percentage of daily target
    carb_percentage: float = Field(..., ge=0, le=100)  # Percentage of daily target
    fiber_percentage: float = Field(..., ge=0, le=100)  # Percentage of daily target
    description: Optional[str] = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Nutrition Comparison schemas
class NutritionComparisonBase(BaseModel):
    food_id: str
    target_id: str

class NutritionComparisonCreate(NutritionComparisonBase):
    pass

class NutritionComparisonResponse(MongoBaseModel):
    food_id: str
    target_id: str
    diff_calories: float
    diff_protein: float
    diff_fat: float
    diff_carb: float
    diff_fiber: float
    compared_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Nutrition Review schemas
class NutritionReviewBase(BaseModel):
    protein_comment: str
    fat_comment: str
    carb_comment: str
    fiber_comment: str
    calories_comment: str
    score: Optional[int] = Field(70, ge=0, le=100)
    strengths: Optional[List[str]] = []
    weaknesses: Optional[List[str]] = []

class NutritionReviewCreate(NutritionReviewBase):
    pass

class NutritionReviewResponse(MongoBaseModel, NutritionReviewBase):
    comparison_id: str
    food_id: Optional[str] = None
    target_id: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Advise schemas
class SubstitutionItem(BaseModel):
    original: str
    substitute: str
    benefit: str

class AdviseBase(BaseModel):
    recommendations: List[str]
    substitutions: List[SubstitutionItem]
    tips: List[str]

class AdviseCreate(AdviseBase):
    pass

class AdviseResponse(MongoBaseModel, AdviseBase):
    comparison_id: str
    food_id: Optional[str] = None
    target_id: Optional[str] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Daily Report schemas
class DailyReportBase(BaseModel):
    report_date: date
    total_calories: float
    total_protein: float
    total_fat: float
    total_carb: float
    total_fiber: float
    avg_nutrition_score: Optional[float] = 0

class DailyReportCreate(DailyReportBase):
    pass

class DailyReportResponse(MongoBaseModel, DailyReportBase):
    user_id: str

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Weekly Report schemas
class WeeklyReportBase(BaseModel):
    week_start_date: date
    week_end_date: date
    avg_calories: float
    avg_protein: float
    avg_fat: float
    avg_carb: float
    avg_fiber: float
    avg_nutrition_score: Optional[float] = 0

class WeeklyReportCreate(WeeklyReportBase):
    pass

class WeeklyReportResponse(MongoBaseModel, WeeklyReportBase):
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Weekly Ingredient Usage schemas
class WeeklyIngredientUsageBase(BaseModel):
    ingredient_id: str
    usage_count: int
    total_quantity: float

class WeeklyIngredientUsageCreate(WeeklyIngredientUsageBase):
    pass

class WeeklyIngredientUsageResponse(MongoBaseModel, WeeklyIngredientUsageBase):
    weekly_report_id: str

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Weekly Report Comment schemas
class ChartTypeEnum(str, Enum):
    calories = "calories"
    protein = "protein"
    fat = "fat"
    carb = "carb"
    fiber = "fiber"
    ingredients = "ingredients"

class WeeklyReportCommentBase(BaseModel):
    chart_type: ChartTypeEnum
    comment: str
    suggestions: str

class WeeklyReportCommentCreate(WeeklyReportCommentBase):
    pass

class WeeklyReportCommentResponse(MongoBaseModel, WeeklyReportCommentBase):
    weekly_report_id: str

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Food image upload and recognition schemas
class FoodImageUpload(BaseModel):
    image_url: str

class IngredientRecognition(BaseModel):
    name: str
    quantity: float
    unit: str
    protein: float
    fat: float
    carb: float
    fiber: float
    calories: float
    did_you_know: Optional[str] = None

class FoodRecognitionResponse(BaseModel):
    food_name: str
    meal_type: Optional[str] = "lunch"
    ingredients: List[IngredientRecognition]
    total_calories: float
    total_protein: float
    total_fat: float
    total_carb: float
    total_fiber: float
    nutrition_score: Optional[int] = None
    nutrition_review: Optional[dict] = None
    nutrition_advice: Optional[dict] = None

# Measurement Unit schemas
class MeasurementUnitBase(BaseModel):
    name: str
    category: str  # weight, volume, quantity, etc.
    conversion_factor: float  # Factor to convert to base unit (e.g., grams)
    base_unit: str  # Base unit (e.g., "g" for grams)

class MeasurementUnitCreate(MeasurementUnitBase):
    pass

class MeasurementUnitUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    conversion_factor: Optional[float] = None
    base_unit: Optional[str] = None

class MeasurementUnitResponse(MongoBaseModel, MeasurementUnitBase):
    user_id: Optional[str] = None
    is_default: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Notification schemas
class NotificationBase(BaseModel):
    title: str
    message: str
    type: str  # meal_reminder, weekly_report, nutrition_tip, etc.
    is_read: bool = False
    data: Optional[dict] = None
    
class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(MongoBaseModel, NotificationBase):
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    read_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Notification Settings schemas
class ReminderTimes(BaseModel):
    breakfast: str = "08:00"  # HH:MM format
    lunch: str = "12:00"
    dinner: str = "18:00"

class NotificationSettingsBase(BaseModel):
    meal_reminders: bool = True
    weekly_report: bool = True
    nutrition_tips: bool = True
    progress_updates: bool = True
    marketing: bool = False
    reminder_times: ReminderTimes = Field(default_factory=ReminderTimes)

class NotificationSettingsUpdate(BaseModel):
    meal_reminders: Optional[bool] = None
    weekly_report: Optional[bool] = None
    nutrition_tips: Optional[bool] = None
    progress_updates: Optional[bool] = None
    marketing: Optional[bool] = None
    reminder_times: Optional[ReminderTimes] = None

class NotificationSettingsResponse(MongoBaseModel, NotificationSettingsBase):
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}