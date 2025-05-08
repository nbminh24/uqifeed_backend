from pydantic import BaseModel, Field, root_validator
from typing import Optional, List, Dict
from datetime import date, datetime
from enum import Enum
from src.config.database import PyObjectId
from bson import ObjectId

class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

class ChartTypeEnum(str, Enum):
    CALORIES = "calories"
    PROTEIN = "protein"
    FAT = "fat"
    CARB = "carb"
    FIBER = "fiber"
    INGREDIENTS = "ingredients"

# Daily Report schemas
class DailyReportBase(BaseModel):
    """Base schema for daily reports"""
    report_date: date
    total_calories: float
    total_protein: float
    total_fat: float
    total_carb: float
    total_fiber: float
    avg_nutrition_score: Optional[float] = 0

class DailyReportCreate(DailyReportBase):
    """Schema for creating a new daily report"""
    user_id: str

class DailyReportResponse(DailyReportBase, MongoBaseModel):
    """Schema for daily report response"""
    user_id: str
    created_at: Optional[datetime] = None

# Weekly Report schemas
class WeeklyReportBase(BaseModel):
    """Base schema for weekly reports"""
    week_start_date: date
    week_end_date: date
    avg_calories: float
    avg_protein: float
    avg_fat: float
    avg_carb: float
    avg_fiber: float
    avg_nutrition_score: Optional[float] = 0

class WeeklyReportCreate(WeeklyReportBase):
    """Schema for creating a new weekly report"""
    user_id: str

class WeeklyReportResponse(WeeklyReportBase, MongoBaseModel):
    """Schema for weekly report response"""
    user_id: str
    created_at: Optional[datetime] = None

# Weekly Ingredient Usage schemas
class WeeklyIngredientUsageBase(BaseModel):
    """Base schema for weekly ingredient usage"""
    ingredient_id: str
    usage_count: int
    total_quantity: float

class WeeklyIngredientUsageCreate(WeeklyIngredientUsageBase):
    """Schema for creating a new weekly ingredient usage"""
    report_id: str

class WeeklyIngredientUsageResponse(WeeklyIngredientUsageBase, MongoBaseModel):
    """Schema for weekly ingredient usage response"""
    report_id: str
    created_at: Optional[datetime] = None

# Weekly Report Comment schemas
class WeeklyReportCommentBase(BaseModel):
    """Base schema for weekly report comments"""
    chart_type: ChartTypeEnum
    comment: str
    suggestions: str

class WeeklyReportCommentCreate(WeeklyReportCommentBase):
    """Schema for creating a new weekly report comment"""
    report_id: str

class WeeklyReportCommentResponse(WeeklyReportCommentBase, MongoBaseModel):
    """Schema for weekly report comment response"""
    report_id: str
    created_at: Optional[datetime] = None

# Nutrition Target schemas
class NutritionTargetBase(BaseModel):
    """Base schema for nutrition targets"""
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
    """Schema for creating a new nutrition target"""
    user_id: str

class NutritionTargetUpdate(BaseModel):
    """Schema for updating a nutrition target - all fields optional"""
    target_calories: Optional[float] = None
    target_protein: Optional[float] = None
    target_fat: Optional[float] = None
    target_carb: Optional[float] = None
    target_fiber: Optional[float] = None

class NutritionTargetDetail(BaseModel):
    """Schema for nutrition target details"""
    calories: float
    protein: float  # in grams
    fat: float  # in grams
    carb: float  # in grams
    fiber: float  # in grams

class NutritionTargetDetailResponse(NutritionTargetDetail, MongoBaseModel):
    """Schema for nutrition target details response"""
    user_id: str
    macro_ratio: Dict[str, float]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Nutrition Comparison schemas
class NutritionComparisonBase(BaseModel):
    """Base schema for nutrition comparisons"""
    food_id: str
    target_id: str

# Nutrition Review schemas
class NutritionReviewBase(BaseModel):
    """Base schema for nutrition reviews"""
    protein_comment: str
    fat_comment: str
    carb_comment: str
    fiber_comment: str
    calories_comment: str
    score: Optional[int] = Field(70, ge=0, le=100)
    strengths: Optional[List[str]] = []
    weaknesses: Optional[List[str]] = []

class NutritionReviewCreate(NutritionReviewBase):
    """Schema for creating a new nutrition review"""
    food_id: str

class NutritionReviewResponse(NutritionReviewBase, MongoBaseModel):
    """Schema for nutrition review response"""
    food_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Advise schemas
class SubstitutionItem(BaseModel):
    """Schema for substitution items"""
    original: str
    substitute: str
    benefit: str

class AdviseBase(BaseModel):
    """Base schema for advises"""
    recommendations: List[str]
    substitutions: List[SubstitutionItem]
    tips: List[str]

class AdviseCreate(AdviseBase):
    """Schema for creating a new advise"""
    food_id: str

class AdviseResponse(AdviseBase, MongoBaseModel):
    """Schema for advise response"""
    food_id: str
    created_at: Optional[datetime] = None

class MeasurementUnitBase(BaseModel):
    """Schema for measurement units"""
    name: str
    category: str  # weight, volume, quantity, etc.
    conversion_factor: float  # Factor to convert to base unit (e.g., grams)
    base_unit: str  # Base unit (e.g., "g" for grams)

class ChartTypeEnum(str, Enum):
    """Enum for chart types in reports"""
    CALORIES = "calories"
    PROTEIN = "protein"
    FAT = "fat"
    CARB = "carb"
    FIBER = "fiber"
    INGREDIENTS = "ingredients"

class WeeklyReportCommentBase(BaseModel):
    """Base schema for weekly report comments"""
    chart_type: ChartTypeEnum
    comment: str
    suggestions: str