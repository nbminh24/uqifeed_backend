from fastapi import FastAPI
from src.services.save_dish import save_dish_to_db, DishRequest

# Khởi tạo FastAPI
app = FastAPI()

@app.post("/save_dish/")
async def save_dish(dish: DishRequest):
    return await save_dish_to_db(dish)
