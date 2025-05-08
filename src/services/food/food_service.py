import os
import shutil
from fastapi import UploadFile, HTTPException, Depends
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClientSession
import asyncio
from functools import lru_cache
import json

from src.config.database import ingredients_collection, foods_collection, get_db
from src.schemas.food.food_schema import FoodCreate, FoodUpdate
from src.schemas.dish import DishRequest, IngredientRecognition
from src.utils.db_utils import safe_db_operation

# Cache settings
CACHE_TTL = 300  # 5 minutes
CACHE_SIZE = 1000

def validate_food_data(food_data: Dict) -> tuple[bool, str]:
    """
    Validate food data before saving
    """
    required_fields = ["food_name", "meal_type", "total_calories"]
    for field in required_fields:
        if field not in food_data:
            return False, f"Missing required field: {field}"
    
    if not isinstance(food_data.get("total_calories"), (int, float)) or food_data["total_calories"] < 0:
        return False, "Invalid total calories value"
    
    if not isinstance(food_data.get("ingredients", []), list):
        return False, "Ingredients must be a list"
    
    return True, ""

@lru_cache(maxsize=CACHE_SIZE)
def get_cached_food(food_id: str) -> Optional[Dict]:
    """
    Get food from cache
    """
    return None  # Implement actual caching logic here

async def save_new_dish_to_db(
    dish_request: DishRequest,
    show_loading: bool = True
) -> Dict:
    """
    Process a dish recognized by Gemini API and save it as a new dish to the database
    
    Args:
        dish_request: Dish recognition request with text data from Gemini API
        show_loading: Whether to return loading screen status
        
    Returns:
        Saved food data
    """
    try:
        # Validate request
        if not dish_request.food_data:
            raise HTTPException(status_code=400, detail="Food data must be provided")
        
        # Validate food data
        is_valid, error_message = validate_food_data(dish_request.food_data)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)
        
        now = datetime.utcnow()
        food_data = dish_request.food_data
        
        # Create food document
        food_doc = {
            "name": food_data.get("food_name", "Unknown Food"),
            "user_id": dish_request.user_id,
            "meal_type": food_data.get("meal_type", "lunch"),
            "eating_time": food_data.get("eating_time", now),
            "description": food_data.get("description", ""),
            "image_url": dish_request.image_url,
            "total_calories": food_data.get("total_calories", 0),
            "total_protein": food_data.get("total_protein", 0),
            "total_fat": food_data.get("total_fat", 0),
            "total_carb": food_data.get("total_carb", 0),
            "total_fiber": food_data.get("total_fiber", 0),
            "created_at": now,
            "updated_at": now
        }
        
        # Process ingredients
        ingredients = food_data.get("ingredients", [])
        ingredient_refs = []
        
        # Use transaction for atomic operation
        async with await get_db().client.start_session() as session:
            async with session.start_transaction():
                # Insert new food document
                food_result = await safe_db_operation(
                    foods_collection.insert_one(food_doc, session=session)
                )
                food_id = food_result.inserted_id
                
                # Process ingredients
                for ing in ingredients:
                    # Create ingredient document
                    ingredient_doc = {
                        "food_id": food_id,
                        "name": ing.get("name", "Unknown Ingredient"),
                        "quantity": ing.get("quantity", 0),
                        "unit": ing.get("unit", "g"),
                        "protein": ing.get("protein", 0),
                        "fat": ing.get("fat", 0),
                        "carb": ing.get("carb", 0),
                        "fiber": ing.get("fiber", 0),
                        "calories": ing.get("calories", 0),
                        "did_you_know": ing.get("did_you_know", ""),
                        "created_at": now,
                        "updated_at": now
                    }
                    
                    # Insert ingredient
                    ingredient_result = await safe_db_operation(
                        ingredients_collection.insert_one(ingredient_doc, session=session)
                    )
                    
                    # Add reference to the list
                    ingredient_refs.append({
                        "ingredient_id": str(ingredient_result.inserted_id),
                        "name": ing.get("name", "Unknown Ingredient"),
                        "quantity": ing.get("quantity", 0),
                        "unit": ing.get("unit", "g"),
                        "did_you_know": ing.get("did_you_know", "")
                    })
                
                # Update food with ingredients
                await safe_db_operation(
                    foods_collection.update_one(
                        {"_id": food_id},
                        {"$set": {"ingredients": ingredient_refs}},
                        session=session
                    )
                )
        
        # Prepare response
        food_doc["id"] = str(food_id)
        food_doc["ingredients"] = ingredient_refs
        
        response = {
            "status": "success",
            "message": "Dish saved successfully",
            "food_id": str(food_id),
            "food_name": food_doc["name"],
            "total_calories": food_doc["total_calories"],
            "total_protein": food_doc["total_protein"],
            "total_fat": food_doc["total_fat"],
            "total_carb": food_doc["total_carb"],
            "total_fiber": food_doc["total_fiber"]
        }
        
        # Add loading screen status if requested
        if show_loading:
            response["loading"] = False
            
        return response
    
    except Exception as e:
        # Log detailed error
        error_details = {
            "error": str(e),
            "user_id": dish_request.user_id,
            "food_name": dish_request.food_data.get("food_name") if dish_request.food_data else None,
            "timestamp": datetime.utcnow().isoformat()
        }
        print(f"Error saving dish: {json.dumps(error_details)}")
        
        # If showing loading screen, update status even on error
        if show_loading:
            return {
                "status": "error",
                "message": f"Error saving dish: {str(e)}",
                "loading": False
            }
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
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/gif"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
            )
        
        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB
        file_size = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        
        # Create uploads directory if it doesn't exist
        uploads_dir = "uploads"
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        
        # Generate a unique filename with UUID
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(uploads_dir, unique_filename)
        
        # Save the file with size validation
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > max_size:
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=400,
                        detail="File size exceeds maximum limit of 5MB"
                    )
                buffer.write(chunk)
        
        return file_path
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading file: {str(e)}")

async def search_foods(
    user_id: Optional[str] = None,
    name: Optional[str] = None, 
    category: Optional[str] = None,
    meal_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0, 
    limit: int = 100,
    sort_field: str = "eating_time",
    sort_direction: int = -1
) -> List[Dict[str, Any]]:
    """
    Unified search function for foods with comprehensive filtering options
    
    Args:
        user_id: Optional filter by user ID
        name: Optional filter by food name
        category: Optional filter by food category
        meal_type: Optional filter by meal type
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        skip: Number of records to skip
        limit: Maximum number of records to return
        sort_field: Field to sort by
        sort_direction: Sort direction (1 for ascending, -1 for descending)
    
    Returns:
        List[Dict]: List of foods matching the criteria
    """
    try:
        # Validate input parameters
        if skip < 0:
            raise HTTPException(status_code=400, detail="Skip value cannot be negative")
        if limit < 1 or limit > 1000:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 1000")
        if sort_direction not in [1, -1]:
            raise HTTPException(status_code=400, detail="Sort direction must be 1 or -1")
        
        # Build query filter
        query = {}
        
        # Filter by user ID if provided
        if user_id:
            query["user_id"] = user_id
        
        # Filter by name if provided (case-insensitive search)
        if name:
            query["name"] = {"$regex": name, "$options": "i"}
        
        # Filter by category if provided
        if category:
            query["category"] = category
        
        # Filter by meal type if provided
        if meal_type:
            query["meal_type"] = meal_type
        
        # Filter by date range if provided
        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = start_date
            if end_date:
                date_query["$lte"] = end_date
            query["eating_time"] = date_query
        
        # Execute query with pagination and sorting
        foods = await safe_db_operation(
            foods_collection.find(query)
            .sort(sort_field, sort_direction)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )
        
        # Convert ObjectId to string
        for food in foods:
            food["id"] = str(food["_id"])
        
        return foods
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching foods: {str(e)}")

async def get_food_with_ingredients(food_id: str) -> Dict:
    """
    Get food with its ingredients
    
    Args:
        food_id: Food ID
        
    Returns:
        Food data with ingredients
    """
    try:
        # Check cache first
        cached_food = get_cached_food(food_id)
        if cached_food:
            return cached_food
        
        # Get food details
        food = await safe_db_operation(
            foods_collection.find_one({"_id": ObjectId(food_id)})
        )
        
        if not food:
            raise HTTPException(status_code=404, detail="Food not found")
        
        # Get ingredients
        ingredients = await safe_db_operation(
            ingredients_collection.find({"food_id": ObjectId(food_id)}).to_list(length=None)
        )
        
        # Convert ObjectId to string
        food["id"] = str(food["_id"])
        for ingredient in ingredients:
            ingredient["id"] = str(ingredient["_id"])
        
        # Add ingredients to food
        food["ingredients"] = ingredients
        
        return food
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting food details: {str(e)}")

async def update_food(food_id: str, food_update: FoodUpdate) -> Dict[str, Any]:
    """
    Update a food item and its ingredients
    
    Args:
        food_id: ID of food to update
        food_update: Food update data including ingredients information
    
    Returns:
        Dict: Updated food with ingredients
    """
    try:
        # Validate food exists
        food = await safe_db_operation(
            foods_collection.find_one({"_id": ObjectId(food_id)})
        )
        
        if not food:
            raise HTTPException(status_code=404, detail="Food not found")
        
        # Prepare update data
        update_data = food_update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        # Use transaction for atomic operation
        async with await get_db().client.start_session() as session:
            async with session.start_transaction():
                # Update food
                await safe_db_operation(
                    foods_collection.update_one(
                        {"_id": ObjectId(food_id)},
                        {"$set": update_data},
                        session=session
                    )
                )
                
                # Update ingredients if provided
                if food_update.ingredients:
                    # Delete existing ingredients
                    await safe_db_operation(
                        ingredients_collection.delete_many(
                            {"food_id": ObjectId(food_id)},
                            session=session
                        )
                    )
                    
                    # Insert new ingredients
                    for ingredient in food_update.ingredients:
                        ingredient_doc = {
                            "food_id": ObjectId(food_id),
                            "name": ingredient.name,
                            "quantity": ingredient.quantity,
                            "unit": ingredient.unit,
                            "protein": ingredient.protein,
                            "fat": ingredient.fat,
                            "carb": ingredient.carb,
                            "fiber": ingredient.fiber,
                            "calories": ingredient.calories,
                            "did_you_know": ingredient.did_you_know,
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                        await safe_db_operation(
                            ingredients_collection.insert_one(
                                ingredient_doc,
                                session=session
                            )
                        )
        
        # Get updated food
        updated_food = await get_food_with_ingredients(food_id)
        
        return updated_food
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating food: {str(e)}")

async def delete_food(food_id: str) -> bool:
    """
    Delete a food item
    
    Args:
        food_id: ID of food to delete
    
    Returns:
        bool: True if deleted, False otherwise
    """
    try:
        # Validate food exists
        food = await safe_db_operation(
            foods_collection.find_one({"_id": ObjectId(food_id)})
        )
        
        if not food:
            raise HTTPException(status_code=404, detail="Food not found")
        
        # Use transaction for atomic operation
        async with await get_db().client.start_session() as session:
            async with session.start_transaction():
                # Delete food
                await safe_db_operation(
                    foods_collection.delete_one(
                        {"_id": ObjectId(food_id)},
                        session=session
                    )
                )
                
                # Delete ingredients
                await safe_db_operation(
                    ingredients_collection.delete_many(
                        {"food_id": ObjectId(food_id)},
                        session=session
                    )
                )
        
        # Delete associated image if exists
        if food.get("image_url"):
            try:
                os.remove(food["image_url"])
            except OSError:
                pass  # Ignore if file doesn't exist
        
        return True
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting food: {str(e)}")