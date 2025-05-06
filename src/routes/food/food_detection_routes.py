from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Form
from typing import Optional, List
import os
import uuid
from datetime import datetime

from src.services.authentication.user_auth import get_current_user
from src.services.food import detect_food_from_image
from src.schemas.food.food_schema import FoodDetectionResponse, FoodItem

# Initialize router
router = APIRouter(
    tags=["food-detection"]
)

@router.post("/detect", response_model=FoodDetectionResponse)
async def detect_food(
    file: UploadFile = File(...),
    model: Optional[str] = Form("gemini-pro-vision"),
    current_user = Depends(get_current_user)
):
    """
    Detect food items from an uploaded image
    
    - **file**: Image file with food
    - **model**: AI model to use for detection (default: gemini-pro-vision)
    """
    # Save uploaded file temporarily
    file_extension = os.path.splitext(file.filename)[1]
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Food detection failed: {str(e)}")