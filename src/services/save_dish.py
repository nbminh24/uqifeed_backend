import os
import json
from src.services.database import get_db
async def ensure_ingredient_exists(db, ingredient_name, nutrition_info):
    """Đảm bảo rằng nguyên liệu tồn tại trong bảng ingredients và cập nhật nếu cần"""
    ingredient = await db.fetchrow("SELECT id FROM ingredients WHERE name = $1", ingredient_name)
    if not ingredient:
        # Thêm nguyên liệu mới nếu không tồn tại
        ingredient_id = await db.fetchval("""
            INSERT INTO ingredients (name, description, protein, fat, carbs, fiber, calories)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING id
        """, ingredient_name, None, float(nutrition_info["protein"].replace("g", "")),
            float(nutrition_info["fat"].replace("g", "")),
            float(nutrition_info["carbs"].replace("g", "")),
            float(nutrition_info["fiber"].replace("g", "")),
            float(nutrition_info["protein"].replace("g", "")) * 4 +
            float(nutrition_info["fat"].replace("g", "")) * 9 +
            float(nutrition_info["carbs"].replace("g", "")) * 4)
        return ingredient_id
    else:
        # Cập nhật thông tin dinh dưỡng nếu nguyên liệu đã tồn tại
        await db.execute("""
            UPDATE ingredients
            SET protein = $2, fat = $3, carbs = $4, fiber = $5, calories = $6
            WHERE id = $1
        """, ingredient["id"], float(nutrition_info["protein"].replace("g", "")),
            float(nutrition_info["fat"].replace("g", "")),
            float(nutrition_info["carbs"].replace("g", "")),
            float(nutrition_info["fiber"].replace("g", "")),
            float(nutrition_info["protein"].replace("g", "")) * 4 +
            float(nutrition_info["fat"].replace("g", "")) * 9 +
            float(nutrition_info["carbs"].replace("g", "")) * 4)
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
                "amount": 100,  # Giả định lượng mặc định là 100g
                "unit": "g"
            })

        return {
            "name": name,
            "description": name,
            "ingredients": processed_ingredients
        }
    except Exception as e:
        raise ValueError(f"Lỗi xử lý dữ liệu: {str(e)}")

async def save_dish_to_db(dish_data):
    """Lưu dữ liệu món ăn vào database"""
    try:
        db = await get_db()
        async with db.transaction():
            # Lưu món ăn
            dish_id = await db.fetchval("""
                INSERT INTO dishes (name, description, user_id)
                VALUES ($1, $2, $3)
                RETURNING id
            """, dish_data["name"], dish_data["description"], 1)  # Giả lập user_id = 1

            # Lưu nguyên liệu vào bảng ingredients và liên kết với dish_ingredients
            for ingredient in dish_data["ingredients"]:
                ingredient_id = await ensure_ingredient_exists(db, ingredient["name"], ingredient["nutrition"])
                await db.execute("""
                    INSERT INTO dish_ingredients (dish_id, ingredient_id, amount, unit)
                    VALUES ($1, $2, $3, $4)
                """, dish_id, ingredient_id, ingredient["amount"], ingredient["unit"])

        return {"status": "success", "message": "Lưu món ăn thành công."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

async def process_detection(detection_result):
    """Xử lý kết quả từ detection.py và lưu vào database"""
    try:
        if detection_result["status"] == "success":
            dish_data = await parse_detection_result(detection_result)
            save_result = await save_dish_to_db(dish_data)
            return save_result
        else:
            return {"status": "error", "message": "Dữ liệu detection không hợp lệ."}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== TEST FUNCTION =====
if __name__ == "__main__":
    import asyncio

    mock_detection_result = {
        "status": "success",
        "response": """{
            "description": "Pizza xúc xích pepperoni cổ điển với phô mai mozzarella tan chảy và lớp vỏ giòn.",
            "ingredients": [
                {
                    "name": "Đế bánh pizza",
                    "nutrition": {
                        "carbs": "30g",
                        "protein": "4g",
                        "fat": "2g",
                        "fiber": "1g"
                    }
                },
                {
                    "name": "Sốt cà chua",
                    "nutrition": {
                        "carbs": "7g",
                        "protein": "1g",
                        "fat": "0g",
                        "fiber": "1g"
                    }
                },
                {
                    "name": "Phô mai Mozzarella",
                    "nutrition": {
                        "carbs": "1g",
                        "protein": "22g",
                        "fat": "22g",
                        "fiber": "0g"
                    }
                },
                {
                    "name": "Xúc xích Pepperoni",
                    "nutrition": {
                        "carbs": "1g",
                        "protein": "20g",
                        "fat": "30g",
                        "fiber": "0g"
                    }
                },
                {
                    "name": "Lá oregano",
                    "nutrition": {
                        "carbs": "4g",
                        "protein": "1g",
                        "fat": "0g",
                        "fiber": "2g"
                    }
                }
            ]
        }"""
    }

    async def test():
        result = await process_detection(mock_detection_result)
        print(result)

    asyncio.run(test())