from pydantic import BaseModel, Field, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from src.config.database import PyObjectId
from bson import ObjectId

# Base MongoDB model
class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id")
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

# Enums
class MealTypeEnum(str, Enum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"
    DRINKS = "drinks"
    LIGHT_MEAL = "light_meal"

class FoodCategory(str, Enum):
    FRUIT = "FRUIT"
    VEGETABLE = "VEGETABLE"
    MEAT = "MEAT"
    SEAFOOD = "SEAFOOD"
    DAIRY = "DAIRY"
    GRAIN = "GRAIN"
    LEGUME = "LEGUME"
    NUT_SEED = "NUT_SEED"
    BEVERAGE = "BEVERAGE"
    SNACK = "SNACK"
    DESSERT = "DESSERT"
    PREPARED_DISH = "PREPARED_DISH"
    OTHER = "OTHER"

# Nutrition Information Schemas
class NutritionInfo(BaseModel):
    calories: float
    protein: float  # in grams
    carbs: float  # in grams
    fat: float  # in grams
    fiber: Optional[float] = None  # in grams
    sugar: Optional[float] = None  # in grams
    sodium: Optional[float] = None  # in milligrams
    cholesterol: Optional[float] = None  # in milligrams
    vitamins: Optional[Dict[str, float]] = None
    minerals: Optional[Dict[str, float]] = None

# Ingredient Schemas
class IngredientBase(BaseModel):
    """Base schema for ingredients"""
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
    """Schema for creating a new ingredient"""
    pass

class IngredientResponse(IngredientBase, MongoBaseModel):
    """Schema for ingredient response"""
    calories: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class FoodIngredientBase(BaseModel):
    """Base schema for food ingredients (association between food and ingredients)"""
    ingredient_id: str
    quantity: float = Field(..., gt=0)

# Food Base Schemas
class FoodBase(BaseModel):
    """Base food schema with common fields"""
    name: str
    description: Optional[str] = None
    category: FoodCategory
    serving_size: float
    serving_unit: str
    nutrition: NutritionInfo

class FoodCreate(FoodBase):
    """Schema for creating a new food item"""
    image_url: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = []

class FoodUpdate(BaseModel):
    """Schema for updating a food item - all fields optional"""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[FoodCategory] = None
    serving_size: Optional[float] = None
    serving_unit: Optional[str] = None
    nutrition: Optional[NutritionInfo] = None
    image_url: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None

class FoodResponse(FoodBase):
    """Schema for food response - used when returning food data"""
    id: str
    image_url: Optional[str] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = []
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

# Dish Schemas
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

class DishResponse(DishBase, MongoBaseModel):
    """Schema for dish response"""
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

# Food Detection and Recognition Schemas
class FoodItem(BaseModel):
    """Schema for detected food item"""
    name: str
    confidence: Optional[float] = None
    description: Optional[str] = None  # Detailed description about ingredients, flavor, and culture
    estimated_nutrition: Optional[Dict] = None

class FoodDetectionResponse(BaseModel):
    """Schema for food detection response"""
    file_name: str
    file_path: str
    model_used: str
    detected_at: datetime
    detected_food: List[FoodItem]

class FoodImageUpload(BaseModel):
    """Schema for food image upload"""
    image_url: str

class IngredientRecognition(BaseModel):
    """Schema for ingredient recognition"""
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
    """Schema for food recognition response"""
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

# API Request Schemas
class DishRequest(BaseModel):
    """Schema for dish recognition request"""
    user_id: str
    image_url: str
    food_data: Optional[Dict] = None

# Meal Type Nutritional Standards schema
class MealTypeNutritionalStandards(BaseModel):
    """Schema for meal type nutritional standards"""
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