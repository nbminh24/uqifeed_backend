from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from datetime import date

from src.schemas.food import (
    FoodResponse, 
    FoodImageUpload, 
    FoodRecognitionResponse
)
from src.schemas.dish import (
    DishRequest
)
from src.services.authentication.user_auth import get_current_user
from src.services.food import (
    upload_dish_image,
    save_new_dish_to_db,
    get_food_with_ingredients,
    search_foods,
    detect_food_from_image
)

# Initialize router
router = APIRouter(
    tags=["dishes"]
)

@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload a food image"""
    file_path = await upload_dish_image(file)
    return {"file_path": file_path}

@router.post("/analyze-uploaded", response_model=FoodRecognitionResponse)
async def analyze_uploaded_image(
    file_path: str = Form(...),
    current_user = Depends(get_current_user)
):
    """Analyze an uploaded food image and return nutritional information"""
    food_data = await detect_food_from_image(file_path)
    return food_data

@router.post("/save-recognized")
async def save_recognized_food(
    dish_request: DishRequest,
    current_user = Depends(get_current_user)
):
    """Save recognized food to database"""
    # Set the user ID from the authenticated user
    dish_request.user_id = current_user["id"]
    
    return await save_new_dish_to_db(dish_request)

@router.get("/{food_id}", response_model=FoodResponse)
async def get_food(
    food_id: str,
    current_user = Depends(get_current_user)
):
    """Get a specific food entry"""
    food = await get_food_with_ingredients(food_id)
    
    # Check if food belongs to the current user
    if food["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this food entry")
    
    return food

@router.get("/", response_model=List[FoodResponse])
async def list_foods(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    meal_type: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """List user's food entries with filtering options"""
    foods = await search_foods(
        user_id=current_user["id"],
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        meal_type=meal_type
    )
    
    return foods