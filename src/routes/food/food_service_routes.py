from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from src.middleware import get_current_user
from src.services.food import search_foods, get_food_with_ingredients, update_food, delete_food
from src.schemas.food.food_schema import FoodUpdate, FoodResponse

# Initialize router
router = APIRouter(
    tags=["food-service"]
)

@router.get("/", response_model=List[FoodResponse])
async def list_foods(
    name: Optional[str] = Query(None, description="Filter by food name"),
    category: Optional[str] = Query(None, description="Filter by food category"),
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    current_user = Depends(get_current_user)
):
    """
    List foods with optional filtering
    
    - **name**: Optional filter by food name (partial match)
    - **category**: Optional filter by food category
    - **skip**: Number of records to skip for pagination
    - **limit**: Maximum number of records to return
    """
    return await search_foods(name=name, category=category, user_id=current_user["id"], skip=skip, limit=limit)

@router.get("/{food_id}", response_model=FoodResponse)
async def get_food(
    food_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get a specific food by ID
    
    - **food_id**: ID of the food to retrieve
    """
    food = await get_food_with_ingredients(food_id)
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    return food

@router.put("/{food_id}", response_model=FoodResponse)
async def edit_food(
    food_id: str,
    food_update: FoodUpdate,
    current_user = Depends(get_current_user)
):
    """
    Update an existing food item
    
    - **food_id**: ID of the food to update
    - **food_update**: Updated food data
    """
    # Check if food exists
    existing_food = await get_food_with_ingredients(food_id)
    if not existing_food:
        raise HTTPException(status_code=404, detail="Food not found")
    
    # Check if user is the creator or has admin privileges
    if existing_food.get("created_by") != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update this food item")
    
    updated_food = await update_food(food_id, food_update)
    return updated_food

@router.delete("/{food_id}", response_model=dict)
async def remove_food(
    food_id: str,
    current_user = Depends(get_current_user)
):
    """
    Delete a food item
    
    - **food_id**: ID of the food to delete
    """
    # Check if food exists
    existing_food = await get_food_with_ingredients(food_id)
    if not existing_food:
        raise HTTPException(status_code=404, detail="Food not found")
    
    # Check if user is the creator or has admin privileges
    if existing_food.get("created_by") != current_user["id"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this food item")
    
    result = await delete_food(food_id)
    return {"message": "Food deleted successfully", "id": food_id}