from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from src.schemas.models import (
    User, UserCreate, UserUpdate,
    Food, FoodCreate, FoodUpdate,
    NutritionTarget, NutritionTargetCreate, NutritionTargetUpdate,
    NutritionComparison, Token, ResponseModel
)
from src.services.authentication.password_manager import (
    authenticate_user, create_user, get_password_hash
)
from src.services.calorie.calorie_service import (
    calculate_dish_calories,
    calculate_meal_calories,
    calculate_nutrition_score,
    generate_strengths,
    generate_weaknesses,
    update_daily_report,
    generate_weekly_report,
    get_weekly_statistics
)
from src.utils.db_utils import (
    create_document,
    get_document,
    update_document,
    delete_document,
    list_documents
)
from src.config.database import (
    users_collection,
    foods_collection,
    nutrition_targets_collection,
    nutrition_comparisons_collection
)
from src.config.schema_constants import STATUS_CODES, API_MESSAGES
from src.utils.validation import validate_date_format
import jwt
from datetime import datetime, timedelta

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Authentication endpoints
@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    success, message = await authenticate_user(form_data.username, form_data.password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": form_data.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/users", response_model=User)
async def register_user(user: UserCreate):
    user_data = user.dict()
    created_user = await create_user(user_data)
    return created_user

# Food endpoints
@router.post("/foods", response_model=Food)
async def create_food(food: FoodCreate, current_user: User = Depends(get_current_user)):
    food_data = food.dict()
    food_data["user_id"] = current_user.id
    food_data["created_at"] = datetime.utcnow()
    food_data["updated_at"] = datetime.utcnow()
    
    created_food = await create_document(foods_collection, food_data)
    return created_food

@router.get("/foods/{food_id}", response_model=Food)
async def get_food(food_id: str, current_user: User = Depends(get_current_user)):
    food = await get_document(
        foods_collection,
        {"_id": food_id, "user_id": current_user.id}
    )
    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=API_MESSAGES["error"]["not_found"]
        )
    return food

@router.put("/foods/{food_id}", response_model=Food)
async def update_food(
    food_id: str,
    food_update: FoodUpdate,
    current_user: User = Depends(get_current_user)
):
    food = await get_document(
        foods_collection,
        {"_id": food_id, "user_id": current_user.id}
    )
    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=API_MESSAGES["error"]["not_found"]
        )
    
    update_data = food_update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    updated_food = await update_document(
        foods_collection,
        {"_id": food_id},
        update_data
    )
    return updated_food

@router.delete("/foods/{food_id}")
async def delete_food(food_id: str, current_user: User = Depends(get_current_user)):
    food = await get_document(
        foods_collection,
        {"_id": food_id, "user_id": current_user.id}
    )
    if not food:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=API_MESSAGES["error"]["not_found"]
        )
    
    await delete_document(foods_collection, {"_id": food_id})
    return {"message": API_MESSAGES["success"]["delete"]}

# Nutrition target endpoints
@router.post("/nutrition-targets", response_model=NutritionTarget)
async def create_nutrition_target(
    target: NutritionTargetCreate,
    current_user: User = Depends(get_current_user)
):
    target_data = target.dict()
    target_data["user_id"] = current_user.id
    target_data["created_at"] = datetime.utcnow()
    target_data["updated_at"] = datetime.utcnow()
    
    created_target = await create_document(nutrition_targets_collection, target_data)
    return created_target

@router.get("/nutrition-targets", response_model=NutritionTarget)
async def get_nutrition_target(current_user: User = Depends(get_current_user)):
    target = await get_document(
        nutrition_targets_collection,
        {"user_id": current_user.id}
    )
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=API_MESSAGES["error"]["not_found"]
        )
    return target

@router.put("/nutrition-targets", response_model=NutritionTarget)
async def update_nutrition_target(
    target_update: NutritionTargetUpdate,
    current_user: User = Depends(get_current_user)
):
    target = await get_document(
        nutrition_targets_collection,
        {"user_id": current_user.id}
    )
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=API_MESSAGES["error"]["not_found"]
        )
    
    update_data = target_update.dict(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    
    updated_target = await update_document(
        nutrition_targets_collection,
        {"user_id": current_user.id},
        update_data
    )
    return updated_target

# Nutrition analysis endpoints
@router.get("/nutrition/meal/{date}/{meal_type}")
async def get_meal_nutrition(
    date: str,
    meal_type: str,
    current_user: User = Depends(get_current_user)
):
    # Validate date format
    is_valid, error_msg = validate_date_format(date)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    meal_data = await calculate_meal_calories(current_user.id, date, meal_type)
    return meal_data

@router.get("/nutrition/daily/{date}")
async def get_daily_nutrition(
    date: str,
    current_user: User = Depends(get_current_user)
):
    # Validate date format
    is_valid, error_msg = validate_date_format(date)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    daily_report = await update_daily_report(current_user.id, date)
    return daily_report

@router.get("/nutrition/weekly/{week_start}")
async def get_weekly_nutrition(
    week_start: str,
    current_user: User = Depends(get_current_user)
):
    # Validate date format
    is_valid, error_msg = validate_date_format(week_start)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    weekly_report = await generate_weekly_report(current_user.id, week_start)
    return weekly_report

@router.get("/nutrition/statistics/{week_start}")
async def get_weekly_statistics(
    week_start: str,
    current_user: User = Depends(get_current_user)
):
    # Validate date format
    is_valid, error_msg = validate_date_format(week_start)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    statistics = await get_weekly_statistics(current_user.id, week_start)
    return statistics

# Helper functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, "your-secret-key", algorithm="HS256")
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=API_MESSAGES["error"]["unauthorized"],
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.JWTError:
        raise credentials_exception
    
    user = await get_document(users_collection, {"email": email})
    if user is None:
        raise credentials_exception
    return user 