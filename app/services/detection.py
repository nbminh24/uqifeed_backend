import google.generativeai as genai
from PIL import Image

# Cấu hình API key
API_KEY = "AIzaSyAQirxCew6bq8R1bNewoj_4PmdOwSjOZVs"
genai.configure(api_key=API_KEY)

# Chọn model hỗ trợ ảnh
model = genai.GenerativeModel("gemini-1.5-pro-latest")
# Mở ảnh cần phân tích (Đọc file dưới dạng PIL Image)
image_path = "./assets/food.webp"  # Thay bằng đường dẫn ảnh của bạn
image = Image.open(image_path)

# Gửi ảnh đến Gemini để nhận diện món ăn
response = model.generate_content(
    ["Hãy mô tả món ăn và nguyên liệu có trong ảnh này.", image],  # Sửa lại cách truyền ảnh
    stream=False
)

# In kết quả
print(response.text)
