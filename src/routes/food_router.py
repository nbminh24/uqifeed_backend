from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from datetime import date, datetime

from src.config.database import get_db, foods_collection, ingredients_collection
from src.schemas.schemas import FoodCreate, FoodResponse, FoodImageUpload, FoodRecognitionResponse
from src.services.auth_service import get_current_user
from src.services.save_dish import DishRequest, save_dish_to_db, upload_dish_image, manual_create_dish
from src.services.detection import process_food_image
from src.services.database import get_user_foods, get_food_with_ingredients

router = APIRouter(
    prefix="/dishes",
    tags=["dishes"],
    dependencies=[Depends(get_current_user)]  # All routes require authentication
)

@router.post("/recognize", response_model=FoodRecognitionResponse)
async def recognize_food(
    image_data: FoodImageUpload,
    current_user = Depends(get_current_user)
):
    """Recognize food from an image URL"""
    food_data = await process_food_image(image_data.image_url)
    return food_data

@router.post("/upload-image")
async def upload_image(
    file: UploadFile = File(...),
    current_user = Depends(get_current_user)
):
    """Upload a food image"""
    file_path = await upload_dish_image(file)
    return {"file_path": file_path}

@router.post("/analyze-uploaded")
async def analyze_uploaded_image(
    file_path: str = Form(...),
    current_user = Depends(get_current_user)
):
    """Analyze an uploaded food image"""
    food_data = await process_food_image(file_path)
    return food_data

@router.post("/", response_model=FoodResponse)
async def create_food(
    food: FoodCreate,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new food entry manually with ingredients"""
    result = await manual_create_dish(food, current_user["id"], db)
    food_id = result["food_id"]
    return await get_food_with_ingredients(food_id)

@router.post("/save-recognized")
async def save_recognized_food(
    dish_request: DishRequest,
    db = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Save recognized food to database"""
    # Set the user ID from the authenticated user
    dish_request.user_id = current_user["id"]
    
    return await save_dish_to_db(dish_request, db)

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
    foods = await get_user_foods(
        user_id=current_user["id"],
        skip=skip,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        meal_type=meal_type
    )
    
    return foods

@router.get("/ingredient/{ingredient_id}", response_model=dict)
async def get_ingredient(
    ingredient_id: str,
    current_user = Depends(get_current_user)
):
    """Get details of a specific ingredient by ID"""
    try:
        from bson import ObjectId
        
        # Convert string ID to ObjectId
        ingredient = await ingredients_collection.find_one({"_id": ObjectId(ingredient_id)})
        
        if not ingredient:
            raise HTTPException(status_code=404, detail="Ingredient not found")
        
        # Convert ObjectId to string
        ingredient["id"] = str(ingredient["_id"])
        
        return ingredient
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving ingredient: {str(e)}")

@router.get("/daily/{date}", response_model=List[FoodResponse])
async def get_daily_meals(
    date: date,
    meal_type: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Get all meals for a specific date with optional filter by meal type"""
    # Chuyển đổi date thành datetime range
    start_datetime = datetime.combine(date, datetime.min.time())
    end_datetime = datetime.combine(date, datetime.max.time())
    
    # Xây dựng query filter
    query = {
        "user_id": current_user["id"],
        "eating_time": {"$gte": start_datetime, "$lte": end_datetime}
    }
    
    # Thêm filter meal_type nếu được chỉ định
    if meal_type:
        query["meal_type"] = meal_type
    
    # Truy vấn danh sách bữa ăn từ database
    meals = await foods_collection.find(query).sort("eating_time", 1).to_list(length=50)
    
    # Thêm trường id cho mỗi bữa ăn
    for meal in meals:
        meal["id"] = str(meal["_id"])
    
    return meals