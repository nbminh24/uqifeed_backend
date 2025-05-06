import os
import shutil
from fastapi import UploadFile, HTTPException, Depends
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid
from bson import ObjectId

from src.config.database import ingredients_collection, foods_collection, get_db
from src.schemas.food.food_schema import FoodCreate, FoodUpdate
from src.schemas.dish import DishRequest, IngredientRecognition

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
        
        # Insert new food document
        food_result = await foods_collection.insert_one(food_doc)
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
                "created_at": now,
                "updated_at": now
            }
            
            # Insert ingredient
            ingredient_result = await ingredients_collection.insert_one(ingredient_doc)
            
            # Add reference to the list
            ingredient_refs.append({
                "ingredient_id": str(ingredient_result.inserted_id),
                "name": ing.get("name", "Unknown Ingredient"),
                "quantity": ing.get("quantity", 0),
                "unit": ing.get("unit", "g")
            })
        
        # Update food with ingredients
        await foods_collection.update_one(
            {"_id": food_id},
            {"$set": {"ingredients": ingredient_refs}} 
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
    
    # Get foods from database with sorting
    cursor = foods_collection.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit)
    foods = await cursor.to_list(length=limit)
    
    # Convert ObjectId to string for each food
    for food in foods:
        food["id"] = str(food["_id"])
    
    return foods

async def get_food_with_ingredients(food_id: str) -> Dict:
    """
    Get food with its ingredients
    
    Args:
        food_id: Food ID
        
    Returns:
        Food data with ingredients
    """
    # Get food document
    food = await foods_collection.find_one({"_id": ObjectId(food_id)})
    
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    
    # Add id field for response
    food["id"] = str(food["_id"])
    
    return food


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
        # Convert model to dict and remove None values
        update_data = {k: v for k, v in food_update.dict(exclude={"ingredients", "nutrition"}) if v is not None}
        update_data["updated_at"] = datetime.utcnow()
        
        # Convert string ID to ObjectId
        object_id = ObjectId(food_id)
        
        # Check if food exists
        existing_food = await foods_collection.find_one({"_id": object_id})
        if not existing_food:
            # Handle nutrition information if provided
            if food_update.nutrition:
    # Convert nutrition model to dict
                update_data["nutrition"] = food_update.nutrition.dict()
    
    # Update total nutrition values based on nutrition info
                if hasattr(food_update.nutrition, "calories"):
                    update_data["total_calories"] = food_update.nutrition.calories
                if hasattr(food_update.nutrition, "protein"):
                    update_data["total_protein"] = food_update.nutrition.protein
                if hasattr(food_update.nutrition, "fat"):
                    update_data["total_fat"] = food_update.nutrition.fat
                if hasattr(food_update.nutrition, "carbs"):
                    update_data["total_carb"] = food_update.nutrition.carbs
                if hasattr(food_update.nutrition, "fiber"):
                    update_data["total_fiber"] = food_update.nutrition.fiber
                raise HTTPException(status_code=404, detail="Food not found for updating")
        
        # Update the food document
        await foods_collection.update_one(
            {"_id": object_id},
            {"$set": update_data}
        )
        
        # Process ingredients if provided
        ingredient_refs = []
        if hasattr(food_update, "ingredients") and food_update.ingredients:
            # Delete existing ingredients
            await ingredients_collection.delete_many({"food_id": object_id})
            
            # Add new ingredients
            now = datetime.utcnow()
            for ing in food_update.ingredients:
                # Create ingredient document
                ingredient_doc = {
                    "food_id": object_id,
                    "name": ing.name,
                    "quantity": ing.quantity,
                    "unit": ing.unit,
                    "protein": ing.protein,
                    "fat": ing.fat,
                    "carb": ing.carb,
                    "fiber": ing.fiber,
                    "calories": ing.calories,
                    "created_at": now,
                    "updated_at": now
                }
                
                # Insert ingredient
                ingredient_result = await ingredients_collection.insert_one(ingredient_doc)
                
                # Add reference to the list
                ingredient_refs.append({
                    "ingredient_id": str(ingredient_result.inserted_id),
                    "name": ing.name,
                    "quantity": ing.quantity,
                    "unit": ing.unit
                })
            
            # Update food with ingredients
            await foods_collection.update_one(
                {"_id": object_id},
                {"$set": {"ingredients": ingredient_refs}}
                # Recalculate total nutrition from ingredients if not provided directly
                if not food_update.nutrition:
                # Calculate totals from ingredients
                    total_calories = sum(ing.calories for ing in food_update.ingredients)
                    total_protein = sum(ing.protein for ing in food_update.ingredients)
                    total_fat = sum(ing.fat for ing in food_update.ingredients)
                    total_carb = sum(ing.carb for ing in food_update.ingredients)
                    total_fiber = sum(ing.fiber for ing in food_update.ingredients)
    
                    # Update food with calculated totals
                    await foods_collection.update_one(
                        {"_id": object_id},
                        {"$set": {
                            "total_calories": total_calories,
                            "total_protein": total_protein,
                            "total_fat": total_fat,
                            "total_carb": total_carb,
                            "total_fiber": total_fiber
                        }}
                )
            )
        
        # Return updated food with ingredients
        updated_food = await foods_collection.find_one({"_id": object_id})
        if updated_food:
            updated_food["id"] = str(updated_food["_id"])
        
        return updated_food
        
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
        # Xóa nguyên liệu liên quan
        await ingredients_collection.delete_many({"food_id": ObjectId(food_id)})
        # Xóa món ăn
        result = await foods_collection.delete_one({"_id": ObjectId(food_id)})
        return result.deleted_count == 1
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting food: {str(e)}")