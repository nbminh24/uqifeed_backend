import os
import pathlib
import google.generativeai as genai
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
import base64
import re
import json
from fastapi import UploadFile, HTTPException
import httpx
import asyncio

load_dotenv()

# Configure the Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Set up the model
generation_config = {
    "temperature": 0.4,
    "top_p": 1,
    "top_k": 32,
    "max_output_tokens": 4096,
}

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",  # Sử dụng model mới nhất thay vì gemini-pro-vision
    generation_config=generation_config,
    safety_settings=safety_settings,
)

async def encode_image_from_url(url: str) -> Optional[str]:
    """Encode an image from URL to base64"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return base64.b64encode(response.content).decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching image from URL: {str(e)}")

async def recognize_food_from_image(image_path_or_url: str) -> Dict[str, Any]:
    """
    Recognize food from an image using Google's Gemini API
    
    Args:
        image_path_or_url: Path to the image or URL
        
    Returns:
        Dictionary containing food name, ingredients, and nutritional information
    """
    try:
        # Determine if the input is a URL or a local path
        img_parts = []
        if image_path_or_url.startswith('http'):
            # It's a URL, download the image
            import requests
            from io import BytesIO
            
            response = requests.get(image_path_or_url)
            img = BytesIO(response.content)
            img_parts = [
                {
                    "mime_type": "image/jpeg",  # Assume JPEG, might need to detect from response headers
                    "data": base64.b64encode(img.getvalue()).decode("utf-8")
                }
            ]
        else:
            # It's a local path
            img = pathlib.Path(image_path_or_url)
            img_parts = [
                {
                    "mime_type": "image/jpeg",  # Assume JPEG, adjust if needed
                    "data": base64.b64encode(img.read_bytes()).decode("utf-8")
                }
            ]
        
        # Prompt for Gemini model
        prompt = """
        Analyze this food image and provide me with the following information in a structured JSON format:
        
        1. The name of the dish
        2. A list of all visible ingredients with their estimated quantities and nutritional data
        3. The total nutritional value breakdown for the entire dish (as served)
        
        For each ingredient, estimate:
        - Quantity in grams or appropriate units
        - Protein (g)
        - Fat (g)
        - Carbohydrates (g)
        - Fiber (g)
        - Calories (kcal)
        
        For the total dish, calculate:
        - Total calories
        - Total protein
        - Total fat
        - Total carbohydrates
        - Total fiber
        
        Return the data as a valid JSON object with the following structure:
        {
            "food_name": "Name of the dish",
            "ingredients": [
                {
                    "name": "Ingredient name",
                    "quantity": 100,
                    "unit": "g",
                    "protein": 10.5,
                    "fat": 5.2,
                    "carb": 25.3,
                    "fiber": 3.1,
                    "calories": 190.4
                }
            ],
            "total_calories": 550,
            "total_protein": 30.5,
            "total_fat": 15.2,
            "total_carb": 75.8,
            "total_fiber": 4.5
        }
        
        Be as precise and accurate as possible, and include all visible ingredients.
        """
        
        # Generate content with the model
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        # Add retry mechanism with exponential backoff
        max_retries = 3
        retry_delay = 5  # initial delay in seconds
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content([prompt, img_parts[0]])
                break
            except Exception as e:
                error_message = str(e)
                if "429" in error_message and attempt < max_retries - 1:
                    # Extract retry delay from error message if available
                    import re
                    retry_seconds = retry_delay
                    retry_match = re.search(r'retry_delay\s*{\s*seconds:\s*(\d+)', error_message)
                    if retry_match:
                        retry_seconds = int(retry_match.group(1))
                    
                    print(f"Rate limit exceeded. Waiting {retry_seconds} seconds before retry...")
                    import asyncio
                    await asyncio.sleep(retry_seconds)
                    retry_delay *= 2  # exponential backoff
                else:
                    # Re-raise the exception for other errors or final attempt
                    raise
        
        # Process the response
        content = response.text
        print(f"Raw response from Gemini API: {content}")
        
        # Clean up the content for JSON parsing
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Parse the JSON response safely
        try:
            food_data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {str(e)}")
            print(f"Content that failed to parse: {content}")
            # Provide a fallback response
            food_data = {
                "food_name": "Unknown food",
                "ingredients": [
                    {
                        "name": "Ingredient 1",
                        "quantity": 100,
                        "unit": "g",
                        "protein": 5,
                        "fat": 5,
                        "carb": 15,
                        "fiber": 2,
                        "calories": 125
                    }
                ],
                "total_calories": 125,
                "total_protein": 5,
                "total_fat": 5,
                "total_carb": 15,
                "total_fiber": 2
            }
        
        # Default to lunch as meal type if not specified
        food_data["meal_type"] = "lunch"
        
        # Cập nhật reviews và lời khuyên có định dạng chi tiết hơn
        food_data["nutrition_review"] = {
            "protein_comment": f"Protein: {food_data['total_protein']}g - Món ăn này cung cấp lượng protein " + 
                              (f"cao, tương đương với {food_data['total_protein']/50*100:.1f}% nhu cầu protein hàng ngày. " +
                              f"Protein trong món ăn chủ yếu đến từ {food_data['ingredients'][0]['name']} và giúp xây dựng và phục hồi cơ bắp."
                              if food_data['total_protein'] >= 20 else
                              f"vừa phải, đáp ứng khoảng {food_data['total_protein']/50*100:.1f}% nhu cầu protein hàng ngày. " +
                              f"Để tăng lượng protein, bạn có thể bổ sung thêm thực phẩm giàu protein như thịt, cá, đậu hoặc các sản phẩm từ sữa."),
            
            "fat_comment": f"Chất béo: {food_data['total_fat']}g - Món ăn này chứa lượng chất béo " +
                          (f"cao, chiếm khoảng {food_data['total_fat']/70*100:.1f}% nhu cầu chất béo hàng ngày. " +
                          f"Bạn nên cân nhắc giảm lượng dầu mỡ trong các bữa ăn tiếp theo."
                          if food_data['total_fat'] > 25 else
                          f"vừa phải, chiếm khoảng {food_data['total_fat']/70*100:.1f}% nhu cầu chất béo hàng ngày. " +
                          f"Chất béo này cung cấp năng lượng và hỗ trợ hấp thu vitamin tan trong chất béo."),
            
            "carb_comment": f"Carbohydrate: {food_data['total_carb']}g - Món ăn này chứa lượng carbohydrate " +
                           (f"cao, chiếm khoảng {food_data['total_carb']/300*100:.1f}% nhu cầu carb hàng ngày. " +
                           f"Carb là nguồn năng lượng chính cho cơ thể và não bộ."
                           if food_data['total_carb'] > 75 else
                           f"khá thấp, chỉ chiếm khoảng {food_data['total_carb']/300*100:.1f}% nhu cầu carb hàng ngày. " + 
                           f"Nếu bạn cần nhiều năng lượng hơn, hãy cân nhắc bổ sung thêm ngũ cốc nguyên hạt, khoai, hoặc các loại đậu."),
            
            "fiber_comment": f"Chất xơ: {food_data['total_fiber']}g - Món ăn này chứa " +
                            (f"nhiều chất xơ, cung cấp khoảng {food_data['total_fiber']/25*100:.1f}% nhu cầu chất xơ hàng ngày. " +
                            f"Chất xơ hỗ trợ tiêu hóa và tạo cảm giác no lâu."
                            if food_data['total_fiber'] > 5 else
                            f"ít chất xơ, chỉ cung cấp khoảng {food_data['total_fiber']/25*100:.1f}% nhu cầu chất xơ hàng ngày. " +
                            f"Bạn nên bổ sung thêm rau, trái cây và ngũ cốc nguyên hạt để tăng lượng chất xơ."),
            
            "calories_comment": f"Calories: {food_data['total_calories']} kcal - Món ăn này cung cấp " +
                               (f"khá nhiều năng lượng, chiếm khoảng {food_data['total_calories']/2000*100:.1f}% nhu cầu calories hàng ngày. " +
                               f"Đây là một bữa ăn no và có thể phù hợp cho người cần nhiều năng lượng."
                               if food_data['total_calories'] > 600 else
                               f"một lượng năng lượng vừa phải, chiếm khoảng {food_data['total_calories']/2000*100:.1f}% nhu cầu calories hàng ngày. " +
                               f"Điều này phù hợp cho một bữa ăn cân bằng.")
        }
        
        food_data["nutrition_advice"] = {
            "recommendations": [
                f"Món {food_data['food_name']} của bạn cung cấp {food_data['total_calories']} calories, {food_data['total_protein']}g protein, " +
                f"{food_data['total_fat']}g chất béo, {food_data['total_carb']}g carbohydrate và {food_data['total_fiber']}g chất xơ.",
                
                "Để cân bằng dinh dưỡng tốt hơn, hãy đảm bảo bữa ăn của bạn chứa protein từ thịt nạc, cá, đậu hoặc các nguồn thực vật; carbohydrate " + 
                "phức hợp từ ngũ cốc nguyên hạt; chất béo lành mạnh từ dầu ô liu, quả bơ, các loại hạt; và nhiều rau xanh để bổ sung vitamin, khoáng chất và chất xơ.",
                
                f"Với {food_data['total_calories']} calories, món ăn này " + 
                (f"khá cân đối cho một bữa ăn chính và cung cấp năng lượng dồi dào." if 400 <= food_data['total_calories'] <= 700 else
                 f"có thể là quá nhẹ cho một bữa ăn chính. Hãy bổ sung thêm thực phẩm giàu dinh dưỡng để đạt đủ năng lượng." if food_data['total_calories'] < 400 else
                 f"khá giàu năng lượng. Nếu bạn đang theo dõi cân nặng, hãy cân nhắc giảm khẩu phần hoặc điều chỉnh các bữa ăn khác trong ngày.")
            ],
            
            "substitutions": [
                {
                    "original": f"Chế biến với nhiều dầu mỡ" if food_data['total_fat'] > 20 else "Các thành phần tinh chế",
                    "substitute": f"Sử dụng phương pháp nấu ít dầu như hấp, luộc hoặc nướng" if food_data['total_fat'] > 20 else "Nguyên liệu tự nhiên, ít qua chế biến",
                    "benefit": f"Giảm lượng chất béo không lành mạnh, hỗ trợ sức khỏe tim mạch" if food_data['total_fat'] > 20 else "Tăng giá trị dinh dưỡng, giảm natri và phụ gia"
                },
                {
                    "original": f"Carbohydrate đơn giản" if food_data['total_carb'] > 60 and food_data['total_fiber'] < 5 else "Protein từ một nguồn duy nhất",
                    "substitute": f"Carbohydrate phức hợp từ ngũ cốc nguyên hạt, rau củ" if food_data['total_carb'] > 60 and food_data['total_fiber'] < 5 else "Kết hợp đa dạng các nguồn protein",
                    "benefit": f"Tăng lượng chất xơ, vitamin và khoáng chất, ổn định đường huyết" if food_data['total_carb'] > 60 and food_data['total_fiber'] < 5 else "Đảm bảo cung cấp đầy đủ các amino acid thiết yếu"
                }
            ],
            
            "tips": [
                f"Món ăn của bạn chứa {food_data['total_protein']}g protein, " + 
                (f"đây là một lượng protein tốt. Protein giúp xây dựng và duy trì cơ bắp, hỗ trợ hệ miễn dịch và tạo cảm giác no lâu." 
                if food_data['total_protein'] >= 15 else 
                f"có thể cân nhắc bổ sung thêm thực phẩm giàu protein như thịt nạc, cá, trứng, đậu hoặc các sản phẩm từ sữa để đạt được lợi ích tối ưu cho sức khỏe và sự phát triển cơ bắp."),
                
                f"Với {food_data['total_carb']}g carbohydrate và {food_data['total_fiber']}g chất xơ, " +
                (f"món ăn có tỷ lệ chất xơ/carb khá tốt. Chất xơ giúp duy trì sức khỏe đường ruột, kiểm soát lượng đường trong máu và tạo cảm giác no lâu."
                if food_data['total_fiber'] >= 5 and food_data['total_carb'] > 0 else
                f"bạn nên bổ sung thêm thực phẩm giàu chất xơ như rau xanh, trái cây, ngũ cốc nguyên hạt để cải thiện sức khỏe tiêu hóa và duy trì cảm giác no lâu hơn."),
                
                f"Món ăn cung cấp {food_data['total_fat']}g chất béo, " +
                (f"nên cân nhắc sử dụng các nguồn chất béo lành mạnh như dầu ô liu, dầu hạt lanh, quả bơ, các loại hạt thay vì chất béo bão hòa hoặc chất béo chuyển hóa."
                if food_data['total_fat'] > 15 else
                f"đây là một lượng vừa phải. Chất béo rất quan trọng cho việc hấp thu vitamin tan trong dầu (A, D, E, K) và cung cấp năng lượng lâu dài.")
            ]
        }
        
        return food_data
    
    except Exception as e:
        print(f"Error in food recognition: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing food image: {str(e)}")

async def process_food_image(file_path_or_url: str) -> Dict[str, Any]:
    """Process a food image and return nutritional information"""
    try:
        food_data = await recognize_food_from_image(file_path_or_url)
        
        # Thêm thông tin "Did You Know" cho mỗi nguyên liệu
        for ingredient in food_data["ingredients"]:
            # Tạo thông tin văn hóa thực phẩm cho nguyên liệu
            ingredient["did_you_know"] = await generate_ingredient_did_you_know(ingredient["name"])
        
        return food_data
    except Exception as e:
        print(f"Error processing food image: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing food image: {str(e)}")

async def generate_ingredient_did_you_know(ingredient_name: str) -> str:
    """
    Generate a 'Did You Know' cultural fact about an ingredient using Gemini API
    
    Args:
        ingredient_name: Name of the ingredient
        
    Returns:
        A string with cultural facts about the ingredient
    """
    try:
        prompt = f"""
        Generate a fascinating 'Did You Know' fact about {ingredient_name} in food culture around the world. 
        Focus on how this ingredient is used in different cuisines globally, its cultural significance, 
        interesting cooking techniques, or traditional dishes that feature it.
        
        The response should be 3-5 sentences, engaging and educational, in the style of a food cultural note.
        Start the response with "Did You Know?" and then provide interesting cultural context.
        
        Example format:
        "Did You Know?
        In Italian cuisine, clams are the star of the classic dish 'spaghetti alle vongole,' where they're cooked with garlic, olive oil, and white wine. 
        In Japan, asari miso soup features small clams simmered in savory miso broth. 
        Around the world, clams are not just food — they're a cultural experience, celebrated in coastal traditions, street food, and gourmet dining alike."
        """
        
        # Generate content with the model
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        # Add retry mechanism
        max_retries = 2
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    return "Did You Know?\nThis ingredient has a rich culinary history and is used in various traditional dishes around the world. Its unique characteristics make it a versatile component in global cuisines, bringing distinctive flavors and textures to many beloved recipes."
        
        content = response.text.strip()
        
        # If response doesn't start with "Did You Know?", add it
        if not content.startswith("Did You Know?"):
            content = "Did You Know?\n" + content
            
        return content
        
    except Exception as e:
        print(f"Error generating ingredient fact: {str(e)}")
        return "Did You Know?\nThis ingredient has a rich culinary history and is used in various traditional dishes around the world. Its unique characteristics make it a versatile component in global cuisines, bringing distinctive flavors and textures to many beloved recipes."