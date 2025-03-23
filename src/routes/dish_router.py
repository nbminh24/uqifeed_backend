from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Depends
from src.services.detection import process_image
from src.services.save_dish import parse_detection_result, save_dish_to_db
from src.services.database import get_db

import os

# Kiểm tra và tạo thư mục temp nếu chưa tồn tại
if not os.path.exists("temp"):
    os.makedirs("temp")

# Khởi tạo router
dish_router = APIRouter()

@dish_router.post("/detect_dish/")
async def detect_dish(image: UploadFile = File(...)):
    """
    Nhận diện món ăn từ ảnh.
    """
    try:
        # Kiểm tra và tạo thư mục temp nếu chưa tồn tại
        if not os.path.exists("temp"):
            os.makedirs("temp")

        # Lưu tạm file ảnh
        image_path = f"temp/{image.filename}"
        with open(image_path, "wb") as f:
            f.write(await image.read())

        # Gọi hàm xử lý ảnh từ detection.py
        result = process_image(image_path)

        if result["status"] == "success":
            return {"status": "success", "data": result["response"]}
        else:
            raise HTTPException(status_code=400, detail=result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@dish_router.post("/detect_and_save/")
async def detect_and_save(user_id: int, image: UploadFile = File(...), db=Depends(get_db)):
    """
    Nhận diện món ăn từ ảnh và lưu vào database.
    """
    try:
        # Kiểm tra và tạo thư mục temp nếu chưa tồn tại
        if not os.path.exists("temp"):
            os.makedirs("temp")

        # Lưu tạm file ảnh
        image_path = f"temp/{image.filename}"
        with open(image_path, "wb") as f:
            f.write(await image.read())

        # Gọi hàm xử lý ảnh từ detection.py
        result = process_image(image_path)

        if result["status"] != "success":
            raise HTTPException(status_code=400, detail=result["message"])

        # Parse dữ liệu từ kết quả detection
        detection_data = result["response"]
        dish_data = await parse_detection_result({"response": detection_data})

        # Lưu dữ liệu vào database
        save_result = await save_dish_to_db(dish_data)

        if save_result["status"] == "success":
            return {"status": "success", "message": "Món ăn đã được lưu thành công."}
        else:
            raise HTTPException(status_code=400, detail=save_result["message"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Khởi tạo ứng dụng FastAPI
app = FastAPI()

# Gắn router vào ứng dụng
app.include_router(dish_router)