import os
import json
import re
from PIL import Image
from dotenv import load_dotenv
import google.generativeai as genai
import requests
from io import BytesIO
from flask import Flask, request, jsonify  # Thêm Flask để tạo endpoint

# Load API Key từ file .env
load_dotenv()
API_KEY = os.getenv("GENAI_API_KEY")

# Cấu hình Gemini API
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-1.5-pro-latest")

def process_image(image_source):
    """Nhận diện món ăn từ ảnh (file hoặc URL) và trích xuất thông tin dinh dưỡng"""
    try:
        # Kiểm tra nếu image_source là URL
        if image_source.startswith("http://") or image_source.startswith("https://"):
            response = requests.get(image_source)
            response.raise_for_status()  # Kiểm tra lỗi HTTP
            image = Image.open(BytesIO(response.content))
        else:
            # Nếu không phải URL, xử lý như file cục bộ
            image = Image.open(image_source)

        # Prompt yêu cầu trả về dữ liệu có cấu trúc rõ ràng
        prompt = """
        Hãy phân tích món ăn trong ảnh và trả về thông tin dưới định dạng JSON:
        {
            "description": "Mô tả ngắn gọn về món ăn",
            "serves": "Ước lượng số khẩu phần ăn",
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
        serves = parsed_result.get("serves", 1)  # Mặc định là 1 nếu không có
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
            "serves": serves,
            "ingredients": processed_ingredients
        }
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

# Flask app để test trên Postman
app = Flask(__name__)

@app.route('/process-image', methods=['POST'])
def process_image_endpoint():
    data = request.json
    image_source = data.get('image_source')  # Lấy link ảnh hoặc đường dẫn file cục bộ từ request
    if not image_source:
        return jsonify({"status": "error", "message": "Thiếu link ảnh hoặc đường dẫn file cục bộ."}), 400

    # Gọi hàm process_image để xử lý ảnh
    result = process_image(image_source)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)