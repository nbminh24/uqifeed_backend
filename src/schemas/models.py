from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
from src.config.schema_constants import SCHEMA_VALIDATION

class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User's email address")
    name: str = Field(..., min_length=2, max_length=50, description="User's full name")
    age: Optional[int] = Field(None, ge=13, le=120, description="User's age")
    height: Optional[float] = Field(None, ge=100, le=250, description="User's height in cm")
    weight: Optional[float] = Field(None, ge=30, le=300, description="User's weight in kg")

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100, description="User's password")

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=50)
    age: Optional[int] = Field(None, ge=13, le=120)
    height: Optional[float] = Field(None, ge=100, le=250)
    weight: Optional[float] = Field(None, ge=30, le=300)

class UserInDB(UserBase):
    id: str = Field(..., description="User's ID")
    hashed_password: str = Field(..., description="Hashed password")
    is_active: bool = Field(True, description="Whether user is active")
    is_verified: bool = Field(False, description="Whether user is verified")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

class User(UserBase):
    id: str = Field(..., description="User's ID")
    is_active: bool = Field(True, description="Whether user is active")
    is_verified: bool = Field(False, description="Whether user is verified")
    created_at: datetime = Field(..., description="Account creation timestamp")

class FoodBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Food name")
    calories: float = Field(..., ge=0, le=10000, description="Calories per 100g")
    protein: float = Field(..., ge=0, le=500, description="Protein per 100g")
    fat: float = Field(..., ge=0, le=500, description="Fat per 100g")
    carb: float = Field(..., ge=0, le=1000, description="Carbohydrates per 100g")
    fiber: float = Field(..., ge=0, le=100, description="Fiber per 100g")

class FoodCreate(FoodBase):
    meal_type: str = Field(..., description="Type of meal")
    eating_time: datetime = Field(..., description="When the food was eaten")
    quantity: float = Field(..., gt=0, description="Quantity in grams")
    ingredients: Optional[List[Dict[str, Any]]] = Field(None, description="List of ingredients")

class FoodUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    calories: Optional[float] = Field(None, ge=0, le=10000)
    protein: Optional[float] = Field(None, ge=0, le=500)
    fat: Optional[float] = Field(None, ge=0, le=500)
    carb: Optional[float] = Field(None, ge=0, le=1000)
    fiber: Optional[float] = Field(None, ge=0, le=100)
    meal_type: Optional[str] = None
    eating_time: Optional[datetime] = None
    quantity: Optional[float] = Field(None, gt=0)
    ingredients: Optional[List[Dict[str, Any]]] = None

class FoodInDB(FoodBase):
    id: str = Field(..., description="Food ID")
    user_id: str = Field(..., description="User ID")
    meal_type: str = Field(..., description="Type of meal")
    eating_time: datetime = Field(..., description="When the food was eaten")
    quantity: float = Field(..., gt=0, description="Quantity in grams")
    ingredients: Optional[List[Dict[str, Any]]] = Field(None, description="List of ingredients")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

class Food(FoodBase):
    id: str = Field(..., description="Food ID")
    meal_type: str = Field(..., description="Type of meal")
    eating_time: datetime = Field(..., description="When the food was eaten")
    quantity: float = Field(..., gt=0, description="Quantity in grams")
    ingredients: Optional[List[Dict[str, Any]]] = Field(None, description="List of ingredients")

class NutritionTarget(BaseModel):
    calories: float = Field(..., ge=0, description="Daily calorie target")
    protein: float = Field(..., ge=0, description="Daily protein target in grams")
    fat: float = Field(..., ge=0, description="Daily fat target in grams")
    carb: float = Field(..., ge=0, description="Daily carbohydrate target in grams")
    fiber: float = Field(..., ge=0, description="Daily fiber target in grams")

class NutritionTargetCreate(NutritionTarget):
    pass

class NutritionTargetUpdate(BaseModel):
    calories: Optional[float] = Field(None, ge=0)
    protein: Optional[float] = Field(None, ge=0)
    fat: Optional[float] = Field(None, ge=0)
    carb: Optional[float] = Field(None, ge=0)
    fiber: Optional[float] = Field(None, ge=0)

class NutritionTargetInDB(NutritionTarget):
    id: str = Field(..., description="Target ID")
    user_id: str = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

class NutritionComparison(BaseModel):
    food_id: str = Field(..., description="Food ID")
    target_id: str = Field(..., description="Target ID")
    food_name: str = Field(..., description="Food name")
    food_calories: float = Field(..., ge=0)
    food_protein: float = Field(..., ge=0)
    food_fat: float = Field(..., ge=0)
    food_carb: float = Field(..., ge=0)
    food_fiber: float = Field(..., ge=0)
    target_calories: float = Field(..., ge=0)
    target_protein: float = Field(..., ge=0)
    target_fat: float = Field(..., ge=0)
    target_carb: float = Field(..., ge=0)
    target_fiber: float = Field(..., ge=0)
    diff_calories: float = Field(..., description="Difference in calories")
    diff_protein: float = Field(..., description="Difference in protein")
    diff_fat: float = Field(..., description="Difference in fat")
    diff_carb: float = Field(..., description="Difference in carbs")
    diff_fiber: float = Field(..., description="Difference in fiber")

class NutritionComparisonInDB(NutritionComparison):
    id: str = Field(..., description="Comparison ID")
    user_id: str = Field(..., description="User ID")
    created_at: datetime = Field(..., description="Creation timestamp")

class Token(BaseModel):
    access_token: str = Field(..., description="Access token")
    token_type: str = Field("bearer", description="Token type")

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None

class ResponseModel(BaseModel):
    status: str = Field(..., description="Response status")
    message: str = Field(..., description="Response message")
    data: Optional[Any] = Field(None, description="Response data") 