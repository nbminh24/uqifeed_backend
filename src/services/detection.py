import os
import json  # Import json để xử lý dữ liệu JSON
import re  # Import regex để lọc JSON hợp lệ
from PIL import Image  # Import lớp Image từ thư viện Pillow
from dotenv import load_dotenv
import google.generativeai as genai

# Load API Key từ file .env
load_dotenv()
API_KEY = os.getenv("GENAI_API_KEY")

# Cấu hình Gemini API
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

def process_image(image_path):
    """Nhận diện món ăn từ ảnh và trích xuất thông tin dinh dưỡng"""
    try:
        image = Image.open(image_path)

        # Prompt yêu cầu trả về dữ liệu có cấu trúc rõ ràng
        prompt = """
        Hãy phân tích món ăn trong ảnh và trả về thông tin dưới định dạng JSON:
        {
            "description": "Mô tả ngắn gọn về món ăn",
            "ingredients": [
                {
                    "name": "Tên nguyên liệu",
                    "amount": "Số lượng nguyên liệu (g)",
                    "unit": "Đơn vị đo lường (ví dụ: g, ml)",
                    "nutrition": {
                        "carbs": "Tinh bột (g/100g)",
                        "protein": "Protein (g/100g)",
                        "fat": "Chất béo (g/100g)",
                        "fiber": "Chất xơ (g/100g)"
                    }
                },
                ...
            ]
        }
        """
        # Gửi yêu cầu đến Gemini API
        response = model.generate_content([prompt, image], stream=False)

        # Kiểm tra kiểu dữ liệu phản hồi
        print("Type of response:", type(response))
        
        # Kiểm tra phản hồi từ Gemini API
        if not response or not response.text:
            return {"status": "error", "message": "Không có phản hồi từ mô hình."}

        # Lấy nội dung phản hồi từ Gemini
        result = response.text.strip()

        # 🛑 Xóa Markdown block nếu có
        result = re.sub(r"```json|```", "", result).strip()

        # 🛑 Trích xuất JSON hợp lệ từ phản hồi
        match = re.search(r"\{.*\}", result, re.DOTALL)
        if not match:
            return {"status": "error", "message": "Không tìm thấy JSON hợp lệ trong phản hồi."}

        json_text = match.group(0)  # Lấy phần JSON hợp lệ

        # 🛑 Parse JSON và xử lý lỗi nếu có
        try:
            parsed_result = json.loads(json_text)
        except json.JSONDecodeError as e:
            return {"status": "error", "message": f"Lỗi khi parse JSON: {str(e)}"}

        # 🛑 Trích xuất thông tin
        description = parsed_result.get("description", "")
        ingredients = parsed_result.get("ingredients", [])

        # 🛑 Chuẩn hóa thông tin nguyên liệu
        processed_ingredients = [
            {
                "name": ingredient.get("name", ""),
                "amount": ingredient.get("amount", 100),  # Mặc định là 100 nếu không có
                "unit": ingredient.get("unit", "g"),  # Mặc định là "g" nếu không có
                "nutrition": ingredient.get("nutrition", {})
            }
            for ingredient in ingredients
        ]

        return {
            "status": "success",
            "description": description,
            "ingredients": processed_ingredients
        }
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== TEST FUNCTION =====
if __name__ == "__main__":
    test_image_path = "C:/Users/USER/Downloads/test.jpg"
    result = process_image(test_image_path)
    print(result)
