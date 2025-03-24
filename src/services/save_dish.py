import os
import json
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from src.services.database import get_db

async def ensure_ingredient_exists(db, ingredient_name, nutrition_info):
    """Đảm bảo rằng nguyên liệu tồn tại trong bảng ingredients và cập nhật nếu cần"""
    ingredient = await db.fetchrow("SELECT id FROM ingredients WHERE name = $1", ingredient_name)
    if not ingredient:
        # Thêm nguyên liệu mới nếu không tồn tại
        ingredient_id = await db.fetchval("""
            INSERT INTO ingredients (name, description, protein, fat, carbs, fiber)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """, ingredient_name, None, float(nutrition_info["protein"].replace("g", "")),
            float(nutrition_info["fat"].replace("g", "")),
            float(nutrition_info["carbs"].replace("g", "")),
            float(nutrition_info["fiber"].replace("g", "")))
        return ingredient_id
    else:
        # Cập nhật thông tin dinh dưỡng nếu nguyên liệu đã tồn tại
        await db.execute("""
            UPDATE ingredients
            SET protein = $2, fat = $3, carbs = $4, fiber = $5
            WHERE id = $1
        """, ingredient["id"], float(nutrition_info["protein"].replace("g", "")),
            float(nutrition_info["fat"].replace("g", "")),
            float(nutrition_info["carbs"].replace("g", "")),
            float(nutrition_info["fiber"].replace("g", "")))
        return ingredient["id"]

async def parse_detection_result(detection_result):
    """Chuyển đổi kết quả từ detection.py thành dữ liệu có cấu trúc"""
    try:
        # Parse JSON từ kết quả trả về
        data = detection_result.get("response", "{}")
        parsed_data = json.loads(data)

        # Lấy thông tin món ăn và nguyên liệu
        name = parsed_data.get("description", "Món ăn không xác định")
        ingredients = parsed_data.get("ingredients", [])

        # Chuẩn bị dữ liệu nguyên liệu
        processed_ingredients = []
        for ingredient in ingredients:
            processed_ingredients.append({
                "name": ingredient["name"],
                "nutrition": ingredient["nutrition"],
                "amount": float(ingredient.get("amount", 100)),  # Chuyển đổi amount sang float
                "unit": ingredient.get("unit", "g")  # Mặc định là "g"
            })

        return {
            "name": name,
            "description": name,
            "ingredients": processed_ingredients
        }
    except Exception as e:
        raise ValueError(f"Lỗi xử lý dữ liệu: {str(e)}")

async def save_dish_to_db(dish_data, db):
    """
    Lưu dữ liệu món ăn vào bảng dishes và dish_ingredients
    """
    # Lưu món ăn vào bảng dishes
    dish_id = await db.fetchval("""
        INSERT INTO dishes (name, description, user_id)
        VALUES ($1, $2, $3)
        RETURNING id
    """, dish_data["name"], dish_data["description"], 1)  # Giả lập user_id = 1

    # Lấy ảnh đại diện của món ăn
    image_url = dish_data.get("image_url", None)

    # Lưu nguyên liệu vào bảng dish_ingredients
    for ingredient in dish_data["ingredients"]:
        ingredient_id = await ensure_ingredient_exists(db, ingredient["name"], ingredient["nutrition"])

        # Tính toán calories
        protein = float(ingredient["nutrition"]["protein"].replace("g", ""))
        fat = float(ingredient["nutrition"]["fat"].replace("g", ""))
        carbs = float(ingredient["nutrition"]["carbs"].replace("g", ""))
        amount = float(ingredient["amount"])  # Chuyển đổi amount từ chuỗi sang số
        calories = (protein * 4 + fat * 9 + carbs * 4) * (amount / 100)

        # Lưu vào bảng dish_ingredients
        await db.execute("""
            INSERT INTO dish_ingredients (dish_id, ingredient_id, amount, unit, image_url, calories)
            VALUES ($1, $2, $3, $4, $5, $6)
        """, dish_id, ingredient_id, amount, ingredient["unit"], image_url, calories)

    return dish_id

# ===== TEST FUNCTION =====
if __name__ == "__main__":
    import asyncio

    mock_detection_result = {
        "status": "success",
        "response": """{
            "description": "Bữa sáng với trứng ốp la, xúc xích, pate, thịt viên sốt cà chua và bánh mì",
            "image_url": "C:/Users/USER/Downloads/test.jpg",
            "ingredients": [
                {
                    "name": "Trứng gà",
                    "amount": "100",
                    "unit": "g",
                    "nutrition": {
                        "carbs": "1.1",
                        "protein": "13",
                        "fat": "11",
                        "fiber": "0"
                    }
                },
                {
                    "name": "Xúc xích",
                    "amount": "50",
                    "unit": "g",
                    "nutrition": {
                        "carbs": "5",
                        "protein": "12",
                        "fat": "20",
                        "fiber": "1"
                    }
                },
                {
                    "name": "Pate",
                    "amount": "30",
                    "unit": "g",
                    "nutrition": {
                        "carbs": "2",
                        "protein": "10",
                        "fat": "25",
                        "fiber": "0"
                    }
                },
                {
                    "name": "Thịt viên",
                    "amount": "150",
                    "unit": "g",
                    "nutrition": {
                        "carbs": "5",
                        "protein": "20",
                        "fat": "15",
                        "fiber": "1"
                    }
                },
                {
                    "name": "Cà chua",
                    "amount": "100",
                    "unit": "g",
                    "nutrition": {
                        "carbs": "3.9",
                        "protein": "0.9",
                        "fat": "0.2",
                        "fiber": "1.2"
                    }
                },
                {
                    "name": "Bánh mì",
                    "amount": "150",
                    "unit": "g",
                    "nutrition": {
                        "carbs": "50",
                        "protein": "8",
                        "fat": "3",
                        "fiber": "3"
                    }
                },
                {
                    "name": "Dưa chuột",
                    "amount": "50",
                    "unit": "g",
                    "nutrition": {
                        "carbs": "3.6",
                        "protein": "0.7",
                        "fat": "0.1",
                        "fiber": "0.5"
                    }
                },
                {
                    "name": "Cà chua",
                    "amount": "50",
                    "unit": "g",
                    "nutrition": {
                        "carbs": "3.9",
                        "protein": "0.9",
                        "fat": "0.2",
                        "fiber": "1.2"
                    }
                }
            ]
        }"""
    }

    async def test():
        # Parse kết quả nhận diện
        parsed_result = await parse_detection_result(mock_detection_result)

        # Kết nối database
        db = await get_db()

        # Lưu món ăn vào database
        dish_id = await save_dish_to_db(parsed_result, db)

        # Kiểm tra kết quả lưu
        ingredients = await db.fetch("SELECT * FROM dish_ingredients WHERE dish_id = $1", dish_id)
        for ingredient in ingredients:
            print("Nguyên liệu đã lưu:", dict(ingredient))

    asyncio.run(test())