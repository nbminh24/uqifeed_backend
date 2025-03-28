import os
import asyncio
import asyncpg
from quart import Quart, request, jsonify
from hypercorn.config import Config
from hypercorn.asyncio import serve

# Khởi tạo ứng dụng Quart
app = Quart(__name__)

# Cấu hình database
DATABASE_URL = "postgresql://uqifeed:Mimikyu124.@localhost:5432/uqifeed_db"

# Hàm kết nối database (async)
async def get_db():
    return await asyncpg.connect(DATABASE_URL)

async def ensure_ingredient_exists(db, ingredient_name, nutrition_info):
    """Đảm bảo nguyên liệu tồn tại trong bảng ingredients và cập nhật nếu cần"""
    try:
        ingredient = await db.fetchrow("SELECT id FROM ingredients WHERE name = $1", ingredient_name)
        if not ingredient:
            ingredient_id = await db.fetchval(
                """
                INSERT INTO ingredients (name, description, protein, fat, carbs, fiber)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """,
                ingredient_name, None,
                float(nutrition_info["protein"]),
                float(nutrition_info["fat"]),
                float(nutrition_info["carbs"]),
                float(nutrition_info["fiber"])
            )
            return ingredient_id
        else:
            await db.execute(
                """
                UPDATE ingredients
                SET protein = $2, fat = $3, carbs = $4, fiber = $5
                WHERE id = $1
                """,
                ingredient["id"],
                float(nutrition_info["protein"]),
                float(nutrition_info["fat"]),
                float(nutrition_info["carbs"]),
                float(nutrition_info["fiber"])
            )
            return ingredient["id"]
    except Exception as e:
        print(f"Lỗi trong ensure_ingredient_exists: {e}")
        raise

async def save_dish_to_db(dish_data):
    """Lưu dữ liệu món ăn vào bảng dishes và dish_ingredients"""
    try:
        print("Đang lưu món ăn vào bảng dishes...")
        db = await get_db()  # Sử dụng await thay vì async with

        # Lưu món ăn vào bảng dishes
        dish_id = await db.fetchval("""
            INSERT INTO dishes (name, description, user_id, serves, image_url)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """, dish_data["name"], dish_data["description"], 1,  # Giả lập user_id = 1
            int(dish_data["serves"]), dish_data.get("image_url", None))
        print(f"Món ăn đã được lưu với ID: {dish_id}")

        # Lưu nguyên liệu vào bảng dish_ingredients
        for ingredient in dish_data["ingredients"]:
            print(f"Đang xử lý nguyên liệu: {ingredient['name']}")
            ingredient_id = await ensure_ingredient_exists(db, ingredient["name"], ingredient["nutrition"])
            print(f"Nguyên liệu {ingredient['name']} có ID: {ingredient_id}")

            # Lưu vào bảng dish_ingredients
            await db.execute("""
                INSERT INTO dish_ingredients (dish_id, ingredient_id, amount, unit)
                VALUES ($1, $2, $3, $4)
            """, dish_id, ingredient_id, float(ingredient["amount"]), ingredient["unit"])
            print(f"Nguyên liệu {ingredient['name']} đã được lưu vào dish_ingredients.")

        await db.close()  # Đóng kết nối sau khi sử dụng
        return dish_id
    except Exception as e:
        print(f"Lỗi trong save_dish_to_db: {e}")
        raise


@app.route('/save-dish', methods=['POST'])
async def save_dish_endpoint():
    try:
        dish_data = await request.get_json()
        if not dish_data:
            return jsonify({"status": "error", "message": "Dữ liệu không hợp lệ."}), 400

        required_fields = ["name", "description", "ingredients", "serves"]
        for field in required_fields:
            if field not in dish_data:
                return jsonify({"status": "error", "message": f"Thiếu trường bắt buộc: {field}"}), 400

        dish_id = await save_dish_to_db(dish_data)
        return jsonify({"status": "success", "dish_id": dish_id})
    except Exception as e:
        print(f"Lỗi: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    config = Config()
    config.bind = ["0.0.0.0:5000"]
    asyncio.run(serve(app, config))
