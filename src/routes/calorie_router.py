from fastapi import FastAPI, APIRouter, HTTPException, Depends
from src.services.database import get_db
from src.services.calorie_service import calculate_dish_calories, calculate_total_nutrition, calculate_meal_calories

# Khởi tạo router
calorie_router = APIRouter()

@calorie_router.get("/calculate_dish_calories/")
async def calculate_dish_calories_endpoint(id: int, db=Depends(get_db)):
    """
    Tính toán lượng calo của một món ăn dựa trên thông tin đã lưu trong database và lưu kết quả vào bảng dish_ingredients.
    """
    try:
        # Truy vấn thông tin món ăn từ database
        query = """
            SELECT dish_ingredients.id AS dish_ingredient_id, protein, fat, carbs, amount
            FROM ingredients
            JOIN dish_ingredients ON ingredients.id = dish_ingredients.ingredient_id
            WHERE dish_ingredients.dish_id = $1
        """
        ingredients = await db.fetch(query, id)

        if not ingredients:
            raise HTTPException(status_code=404, detail="Không tìm thấy nguyên liệu cho món ăn")

        total_protein = 0
        total_fat = 0
        total_carbs = 0
        total_calories = 0

        # Tính toán dinh dưỡng và calo cho từng nguyên liệu
        for ingredient in ingredients:
            protein = ingredient["protein"] * ingredient["amount"] / 100
            fat = ingredient["fat"] * ingredient["amount"] / 100
            carbs = ingredient["carbs"] * ingredient["amount"] / 100
            calories = (protein * 4) + (fat * 9) + (carbs * 4)

            # Lưu calo vào bảng dish_ingredients
            update_query = """
                UPDATE dish_ingredients
                SET calories = $1
                WHERE id = $2
            """
            await db.execute(update_query, calories, ingredient["dish_ingredient_id"])

            # Cộng dồn tổng dinh dưỡng
            total_protein += protein
            total_fat += fat
            total_carbs += carbs
            total_calories += calories

        return {
            "dish_id": id,
            "total_protein": total_protein,
            "total_fat": total_fat,
            "total_carbs": total_carbs,
            "total_calories": total_calories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@calorie_router.post("/calculate_meal_calories/")
async def calculate_meal_calories_endpoint(nutrition_record_id: int, db=Depends(get_db)):
    """
    Tính tổng lượng calo của một bữa ăn dựa trên danh sách các món ăn trong nutrition_record_dishes.
    """
    try:
        # Truy vấn danh sách món ăn trong bữa ăn
        query = """
            SELECT dishes.id AS dish_id, ingredients.protein, ingredients.fat, ingredients.carbs, dish_ingredients.amount
            FROM nutrition_record_dishes
            JOIN dishes ON nutrition_record_dishes.dish_id = dishes.id
            JOIN dish_ingredients ON dishes.id = dish_ingredients.dish_id
            JOIN ingredients ON dish_ingredients.ingredient_id = ingredients.id
            WHERE nutrition_record_dishes.nutrition_record_id = $1
        """
        dishes = await db.fetch(query, nutrition_record_id)

        if not dishes:
            raise HTTPException(status_code=404, detail="Không tìm thấy món ăn nào trong bữa ăn")

        # Tính tổng dinh dưỡng của bữa ăn
        nutrition = await calculate_total_nutrition(dishes)

        # Tính tổng calo
        total_calories = await calculate_meal_calories(dishes)

        return {
            "nutrition_record_id": nutrition_record_id,
            "total_protein": nutrition["total_protein"],
            "total_fat": nutrition["total_fat"],
            "total_carbs": nutrition["total_carbs"],
            "total_calories": total_calories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Khởi tạo ứng dụng FastAPI
app = FastAPI()
app.include_router(calorie_router)

# Chạy ứng dụng nếu file được chạy trực tiếp
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)