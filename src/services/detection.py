import os
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
        response = model.generate_content([prompt, image], stream=False)

        return {
            "status": "success",
            "response": response.text if response else "Không có phản hồi từ mô hình."
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ===== TEST FUNCTION =====
if __name__ == "__main__":
    test_image_path = "C:/Users/USER/Downloads/download.jpg"
    result = process_image(test_image_path)
    print(result)