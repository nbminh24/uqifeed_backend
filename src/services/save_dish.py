import os
import shutil
from fastapi import UploadFile, HTTPException, Depends
from datetime import datetime
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
from bson import ObjectId

from src.services.detection import process_food_image
from src.services.database import save_food_and_ingredients
from src.config.database import get_db, ingredients_collection
from src.schemas.schemas import FoodCreate, FoodIngredientCreate

# Define DishRequest class
class DishRequest(BaseModel):
    user_id: Optional[str] = None
    food_name: Optional[str] = None
    meal_type: Optional[str] = None
    eating_time: Optional[datetime] = None
    ingredients: Optional[List] = None
    image_url: Optional[str] = None
    file_path: Optional[str] = None
    image_path: Optional[str] = None

async def save_dish_to_db(dish_request: DishRequest, db = Depends(get_db)):
    """
    Process a dish image and save it to the database
    
    Args:
        dish_request: Dish recognition request
        db: Database session
        
    Returns:
        Saved food data
    """
    try:
        # Validate request
        if not dish_request.image_url and not dish_request.file_path:
            raise HTTPException(status_code=400, detail="Either image_url or file_path must be provided")
        
        # Process the image - recognize food and nutritional information
        if dish_request.image_url:
            food_data = await process_food_image(dish_request.image_url)
        else:
            food_data = await process_food_image(dish_request.file_path)
        
        # Save the food data to the database
        saved_food = await save_food_and_ingredients(
            user_id=dish_request.user_id,
            food_data=food_data,
            image_url=dish_request.image_url
        )
        
        return {
            "status": "success",
            "message": "Dish saved successfully",
            "food_id": saved_food["id"],
            "food_name": saved_food["name"],
            "total_calories": saved_food["total_calories"],
            "total_protein": saved_food["total_protein"],
            "total_fat": saved_food["total_fat"],
            "total_carb": saved_food["total_carb"],
            "total_fiber": saved_food["total_fiber"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving dish: {str(e)}")

async def upload_dish_image(file: UploadFile) -> str:
    """
    Upload a dish image to the server
    
    Args:
        file: Uploaded file
        
    Returns:
        Path to the saved file
    """
    try:
        # Create uploads directory if it doesn't exist
        uploads_dir = "uploads"
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        
        # Generate a unique filename with UUID
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(uploads_dir, unique_filename)
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return file_path
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

async def manual_create_dish(
    dish_data: FoodCreate,
    user_id: str,
    db
) -> Dict[str, Any]:
    """
    Manually create a dish with ingredients
    
    Args:
        dish_data: Food creation data
        user_id: User ID
        db: Database session
        
    Returns:
        Dictionary with saved food information
    """
    try:
        # Convert FoodCreate to the format expected by save_food_and_ingredients
        food_data = {
            "food_name": dish_data.name,
            "total_calories": 0.0,  # Will be calculated from ingredients
            "total_protein": 0.0,
            "total_fat": 0.0,
            "total_carb": 0.0,
            "total_fiber": 0.0,
            "ingredients": []
        }
        
        # Add ingredients and calculate totals
        for ingredient in dish_data.ingredients:
            # Look up ingredient by ID
            db_ingredient = await ingredients_collection.find_one({"_id": ObjectId(ingredient.ingredient_id)})
            if not db_ingredient:
                raise HTTPException(status_code=404, detail=f"Ingredient with ID {ingredient.ingredient_id} not found")
            
            # Calculate nutrient amounts based on quantity
            quantity_ratio = ingredient.quantity / 100.0  # Nutrients are per 100 units
            
            ingredient_data = {
                "name": db_ingredient["name"],
                "quantity": ingredient.quantity,
                "unit": db_ingredient["unit"],
                "protein": db_ingredient["protein"],
                "fat": db_ingredient["fat"],
                "carb": db_ingredient["carb"],
                "fiber": db_ingredient["fiber"],
                "calories": db_ingredient["calories"]
            }
            
            # Add to food totals
            food_data["total_calories"] += db_ingredient["calories"] * quantity_ratio
            food_data["total_protein"] += db_ingredient["protein"] * quantity_ratio
            food_data["total_fat"] += db_ingredient["fat"] * quantity_ratio
            food_data["total_carb"] += db_ingredient["carb"] * quantity_ratio
            food_data["total_fiber"] += db_ingredient["fiber"] * quantity_ratio
            
            food_data["ingredients"].append(ingredient_data)
        
        # Save the food data to the database
        saved_food = await save_food_and_ingredients(
            user_id=user_id,
            food_data=food_data,
            image_url=dish_data.image_url
        )
        
        return {
            "status": "success",
            "message": "Dish saved successfully",
            "food_id": saved_food["id"],
            "food_name": saved_food["name"],
            "total_calories": saved_food["total_calories"],
            "total_protein": saved_food["total_protein"],
            "total_fat": saved_food["total_fat"],
            "total_carb": saved_food["total_carb"],
            "total_fiber": saved_food["total_fiber"]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating dish: {str(e)}")
