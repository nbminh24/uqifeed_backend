from fastapi import FastAPI, APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import date, datetime
from bson import ObjectId

from src.config.database import get_db, foods_collection, nutrition_comparisons_collection, nutrition_reviews_collection, advises_collection, nutrition_targets_collection
from src.schemas.schemas import (
    NutritionComparisonResponse, NutritionReviewResponse, AdviseResponse,
    DailyReportResponse, WeeklyReportResponse, NutritionTargetResponse
)
from src.services.auth_service import get_current_user
from src.services.database import create_nutrition_comparison, update_daily_report, generate_weekly_report, calculate_nutrition_score, generate_strengths, generate_weaknesses, generate_nutrient_comment
from src.services.calorie_service import calculate_dish_calories, calculate_total_nutrition, calculate_meal_calories

# Khởi tạo router
calorie_router = APIRouter(
    prefix="/calories",
    tags=["calories"]
)

@calorie_router.get("/calculate_dish_calories/")
async def calculate_dish_calories_endpoint(
    food_id: str,
    current_user = Depends(get_current_user)
):
    """
    Tính toán lượng calo của một món ăn dựa trên thông tin nguyên liệu
    """
    try:
        # Truy vấn thông tin món ăn từ database
        food = await foods_collection.find_one({"_id": ObjectId(food_id), "user_id": current_user["id"]})
        
        if not food:
            raise HTTPException(status_code=404, detail="Không tìm thấy món ăn")
        
        if not food.get("ingredients"):
            raise HTTPException(status_code=404, detail="Không tìm thấy nguyên liệu cho món ăn")

        total_protein = 0
        total_fat = 0
        total_carbs = 0
        total_calories = 0

        # Tính toán dinh dưỡng và calo cho từng nguyên liệu
        for ingredient in food["ingredients"]:
            protein = ingredient.get("protein", 0) * ingredient.get("quantity", 0) / 100
            fat = ingredient.get("fat", 0) * ingredient.get("quantity", 0) / 100
            carbs = ingredient.get("carb", 0) * ingredient.get("quantity", 0) / 100
            calories = (protein * 4) + (fat * 9) + (carbs * 4)

            # Cộng dồn tổng dinh dưỡng
            total_protein += protein
            total_fat += fat
            total_carbs += carbs
            total_calories += calories

        return {
            "food_id": food_id,
            "total_protein": total_protein,
            "total_fat": total_fat,
            "total_carbs": total_carbs,
            "total_calories": total_calories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Nutrition comparison, advice, and reporting router
nutrition_router = APIRouter(
    prefix="/nutrition",
    tags=["nutrition"],
    dependencies=[Depends(get_current_user)]  # All routes require authentication
)

# Nutrition comparison routes
@nutrition_router.post("/compare/{food_id}", response_model=NutritionComparisonResponse)
async def compare_food(
    food_id: str,
    current_user = Depends(get_current_user)
):
    """Compare food with user's nutrition target"""
    # Check if food exists and belongs to user
    food = await foods_collection.find_one({"_id": ObjectId(food_id)})
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    
    if food["user_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this food entry")
    
    # Create comparison
    comparison = await create_nutrition_comparison(food_id, current_user["id"])
    
    return comparison

@nutrition_router.get("/compare/{comparison_id}/advice", response_model=AdviseResponse)
async def get_advice(
    comparison_id: str,
    current_user = Depends(get_current_user)
):
    """Get advice for a nutrition comparison"""
    try:
        # Check if comparison exists
        comparison = await nutrition_comparisons_collection.find_one({"_id": ObjectId(comparison_id)})
        if not comparison:
            raise HTTPException(status_code=404, detail="Comparison not found")
        
        # Check if food belongs to user
        food = await foods_collection.find_one({"_id": ObjectId(comparison["food_id"])})
        if not food or food["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to access this comparison")
        
        # First check if the food has preloaded advice
        if "nutrition_advice" in food:
            # Create an advice document using the preloaded data
            advice_doc = {
                "comparison_id": comparison_id,
                "food_id": comparison["food_id"],
                "target_id": comparison["target_id"],
                "recommendations": food["nutrition_advice"].get("recommendations", []),
                "substitutions": food["nutrition_advice"].get("substitutions", []),
                "tips": food["nutrition_advice"].get("tips", []),
                "created_at": datetime.utcnow()
            }
            
            # Save the advice to the database
            result = await advises_collection.insert_one(advice_doc)
            advice = await advises_collection.find_one({"_id": result.inserted_id})
            
            # Add id field for Pydantic model
            advice["id"] = str(advice["_id"])
            
            return advice
        
        # If no preloaded advice, check if one exists in database
        advice = await advises_collection.find_one({"comparison_id": comparison_id})
        if not advice:
            # Nếu không tìm thấy advice, tạo một advice mới bằng cách gọi service
            from src.services.gemini_service import generate_advice
            advice_data = await generate_advice(comparison, food)
            
            # Tạo advice document
            advice_doc = {
                "comparison_id": comparison_id,
                "food_id": comparison["food_id"],
                "target_id": comparison["target_id"],
                "recommendations": advice_data.get("recommendations", []),
                "substitutions": advice_data.get("substitutions", []),
                "tips": advice_data.get("tips", []),
                "created_at": datetime.utcnow()
            }
            
            # Lưu vào database
            result = await advises_collection.insert_one(advice_doc)
            advice = await advises_collection.find_one({"_id": result.inserted_id})
        
        # Đảm bảo các trường cần thiết tồn tại
        if not advice.get("recommendations"):
            advice["recommendations"] = ["Cân bằng chế độ ăn để đạt được mục tiêu dinh dưỡng của bạn."]
        
        if not advice.get("substitutions"):
            advice["substitutions"] = [{"original": "Thực phẩm hiện tại", "substitute": "Lựa chọn cân bằng hơn", "benefit": "Cải thiện hồ sơ dinh dưỡng"}]
        
        if not advice.get("tips"):
            advice["tips"] = ["Duy trì chế độ ăn đa dạng và cân bằng."]
        
        # Add id field for Pydantic model
        advice["id"] = str(advice["_id"])
        
        return advice
    except Exception as e:
        # Log lỗi để debug
        import traceback
        print(f"Error in get_advice: {str(e)}")
        print(traceback.format_exc())
        
        # Tạo một advice mặc định nếu có lỗi
        return {
            "id": comparison_id,
            "comparison_id": comparison_id,
            "recommendations": ["Cân bằng chế độ ăn để đạt được mục tiêu dinh dưỡng của bạn."],
            "substitutions": [{"original": "Thực phẩm hiện tại", "substitute": "Lựa chọn cân bằng hơn", "benefit": "Cải thiện hồ sơ dinh dưỡng"}],
            "tips": ["Duy trì chế độ ăn đa dạng và cân bằng."]
        }

@nutrition_router.get("/compare/{comparison_id}/review", response_model=NutritionReviewResponse)
async def get_review(
    comparison_id: str,
    current_user = Depends(get_current_user)
):
    """Get nutritional review for a comparison"""
    try:
        # Check if comparison exists
        comparison = await nutrition_comparisons_collection.find_one({"_id": ObjectId(comparison_id)})
        if not comparison:
            raise HTTPException(status_code=404, detail="Comparison not found")
        
        # Check if food belongs to user
        food = await foods_collection.find_one({"_id": ObjectId(comparison["food_id"])})
        if not food or food["user_id"] != current_user["id"]:
            raise HTTPException(status_code=403, detail="Not authorized to access this comparison")
        
        # First check if the food has preloaded review
        if "nutrition_review" in food:
            # Create a review document using the preloaded data
            review_doc = {
                "comparison_id": comparison_id,
                "food_id": comparison["food_id"],
                "target_id": comparison["target_id"],
                "score": calculate_nutrition_score(comparison),
                "strengths": generate_strengths(comparison),
                "weaknesses": generate_weaknesses(comparison),
                "protein_comment": food["nutrition_review"]["protein_comment"],
                "fat_comment": food["nutrition_review"]["fat_comment"],
                "carb_comment": food["nutrition_review"]["carb_comment"],
                "fiber_comment": food["nutrition_review"]["fiber_comment"],
                "calories_comment": food["nutrition_review"]["calories_comment"],
                "created_at": datetime.utcnow()
            }
            
            # Save the review to the database
            result = await nutrition_reviews_collection.insert_one(review_doc)
            review = await nutrition_reviews_collection.find_one({"_id": result.inserted_id})
            
            # Add id field for Pydantic model
            review["id"] = str(review["_id"])
            
            return review
        
        # If no preloaded review, check if one exists in database
        review = await nutrition_reviews_collection.find_one({"comparison_id": comparison_id})
        if not review:
            # Nếu không tìm thấy review, tạo một review mới bằng cách gọi service
            from src.services.gemini_service import generate_nutrition_comments
            
            # Tạo review sử dụng Gemini API
            gemini_comments = await generate_nutrition_comments(comparison)
            
            # Tạo review document
            review_doc = {
                "comparison_id": comparison_id,
                "food_id": comparison["food_id"],
                "target_id": comparison["target_id"],
                "score": calculate_nutrition_score(comparison),
                "strengths": generate_strengths(comparison),
                "weaknesses": generate_weaknesses(comparison),
                "protein_comment": gemini_comments["protein_comment"],
                "fat_comment": gemini_comments["fat_comment"],
                "carb_comment": gemini_comments["carb_comment"],
                "fiber_comment": gemini_comments["fiber_comment"],
                "calories_comment": gemini_comments["calories_comment"],
                "created_at": datetime.utcnow()
            }
            
            # Lưu vào database
            result = await nutrition_reviews_collection.insert_one(review_doc)
            review = await nutrition_reviews_collection.find_one({"_id": result.inserted_id})
        
        # Add id field for Pydantic model
        review["id"] = str(review["_id"])
        
        return review
    except Exception as e:
        # Log lỗi để debug
        import traceback
        print(f"Error in get_review: {str(e)}")
        print(traceback.format_exc())
        
        # Import các hàm cần thiết
        from src.services.database import calculate_nutrition_score, generate_strengths, generate_weaknesses, generate_nutrient_comment
        
        # Tạo một review mặc định nếu có lỗi
        return {
            "id": comparison_id,
            "comparison_id": comparison_id,
            "food_id": comparison.get("food_id") if comparison else "",
            "target_id": comparison.get("target_id") if comparison else "",
            "score": calculate_nutrition_score(comparison) if comparison else 70,
            "strengths": generate_strengths(comparison) if comparison else ["Balanced nutrition"],
            "weaknesses": generate_weaknesses(comparison) if comparison else ["Minor deviations from targets"],
            "protein_comment": generate_nutrient_comment(comparison, "diff_protein", "protein") if comparison else "No data available",
            "fat_comment": generate_nutrient_comment(comparison, "diff_fat", "fat") if comparison else "No data available",
            "carb_comment": generate_nutrient_comment(comparison, "diff_carb", "carbohydrate") if comparison else "No data available",
            "fiber_comment": generate_nutrient_comment(comparison, "diff_fiber", "fiber") if comparison else "No data available",
            "calories_comment": generate_nutrient_comment(comparison, "diff_calories", "calorie") if comparison else "No data available"
        }

@nutrition_router.get("/target", response_model=NutritionTargetResponse)
async def get_nutrition_target(
    current_user = Depends(get_current_user)
):
    """Get user's nutrition target"""
    target = await nutrition_targets_collection.find_one({"user_id": current_user["id"]})
    if not target:
        raise HTTPException(status_code=404, detail="Nutrition target not found")
    
    # Add id field for Pydantic model
    target["id"] = str(target["_id"])
    
    return target

# Report routes
@nutrition_router.get("/reports/daily/{report_date}", response_model=DailyReportResponse)
async def get_daily_report(
    report_date: date,
    current_user = Depends(get_current_user)
):
    """Get or generate daily report"""
    # Update report with latest data
    report = await update_daily_report(current_user["id"], report_date)
    
    return report

@nutrition_router.get("/reports/weekly/{week_start_date}", response_model=WeeklyReportResponse)
async def get_weekly_report(
    week_start_date: date,
    current_user = Depends(get_current_user)
):
    """Get or generate weekly report"""
    # Generate report
    report = await generate_weekly_report(current_user["id"], week_start_date)
    
    return report

# Khởi tạo ứng dụng FastAPI
app = FastAPI()
app.include_router(calorie_router)
app.include_router(nutrition_router)

# Chạy ứng dụng nếu file được chạy trực tiếp
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)