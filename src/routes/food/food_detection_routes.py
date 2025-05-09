from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from typing import Optional, List
import os
import uuid
from datetime import datetime
import tempfile

from src.services.authentication.user_auth import get_current_user
from src.services.food import detect_food_from_image
from src.schemas.food.food_schema import FoodDetectionResponse, FoodItem
from src.utils.error_handling import handle_api_error, FileUploadError, ERROR_MESSAGES
from src.utils.file_validation import validate_file, get_file_extension
from src.services.food.food_detector import FoodDetector
from src.utils.error_handler import handle_error
from src.utils.rate_limiter import rate_limit
from src.services.food.nutrition_calculator import calculate_nutrient_scores, generate_nutrition_badge

# Initialize router
router = APIRouter(
    tags=["food-detection"]
)

@router.post("/detect")
@handle_error
@rate_limit(max_requests=10, window_seconds=60)
async def detect_food(
    file: UploadFile = File(...),
    meal_type: str = Form(..., description="Type of meal (breakfast, lunch, dinner, snack)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Detect food items in an uploaded image
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
        
    if meal_type not in ["breakfast", "lunch", "dinner", "snack"]:
        raise HTTPException(status_code=400, detail="Invalid meal type")
    
    # Save uploaded file temporarily
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        contents = await file.read()
        temp_file.write(contents)
        temp_file.close()
        
        # Detect food items
        detector = FoodDetector()
        results = await detector.detect_food(temp_file.name, meal_type)
        
        # Add meal type to results
        results["meal_type"] = meal_type
        
        # Calculate nutrition scores and generate badge
        scores = await calculate_nutrient_scores(results, current_user["id"])
        badge = await generate_nutrition_badge(results, current_user["id"])
        
        # Add scores and badge to results
        results["nutrition_scores"] = scores
        results["nutrition_badge"] = badge
        
        return results
        
    finally:
        # Clean up temporary file
        os.unlink(temp_file.name)

@router.post("/detect", response_model=FoodDetectionResponse)
@handle_api_error
async def detect_food_old(
    file: UploadFile = File(...),
    model: Optional[str] = Form("gemini-pro-vision"),
    current_user = Depends(get_current_user)
):
    """
    Detect food items from an uploaded image
    
    - **file**: Image file with food
    - **model**: AI model to use for detection (default: gemini-pro-vision)
    """
    try:
        # Validate file
        validate_file(file)
        
        # Save uploaded file temporarily
        file_extension = get_file_extension(file.content_type)
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        upload_folder = "uploads"
        
        # Ensure upload directory exists
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, unique_filename)
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        try:
            # Detect food items in the image
            detected_food = await detect_food_from_image(file_path, model)
            
            return {
                "file_name": unique_filename,
                "file_path": file_path,
                "model_used": model,
                "detected_at": datetime.utcnow(),
                "detected_food": detected_food
            }
        finally:
            # Clean up temporary file
            try:
                os.remove(file_path)
            except OSError:
                pass  # Ignore if file doesn't exist
                
    except FileUploadError as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Food detection failed",
                "details": str(e)
            }
        )