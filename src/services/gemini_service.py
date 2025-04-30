import google.generativeai as genai
from typing import Dict, Any, List, Optional
import asyncio
from functools import lru_cache
import json  # Thêm import json

from config import config

# Configure the Gemini API with the API key from config
genai.configure(api_key=config.GOOGLE_API_KEY)

# Create a model instance
model = genai.GenerativeModel('gemini-1.5-pro-latest')

async def generate_nutrition_comments(comparison: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate detailed nutrition comments using Google's Gemini API based on comparison data
    
    Args:
        comparison: Dictionary containing nutrition comparison data
        
    Returns:
        Dictionary with detailed comment for each nutrient type
    """
    # Import here to avoid circular imports
    from src.config.database import meal_type_standards_collection
    
    diff_calories = comparison.get("diff_calories", 0)
    diff_protein = comparison.get("diff_protein", 0)
    diff_fat = comparison.get("diff_fat", 0)
    diff_carb = comparison.get("diff_carb", 0)
    diff_fiber = comparison.get("diff_fiber", 0)
    meal_type = comparison.get("meal_type", "lunch")
    
    # Get meal type standard for context
    meal_standard = None
    if meal_type:
        try:
            meal_standard = await meal_type_standards_collection.find_one({"meal_type": meal_type})
        except Exception as e:
            print(f"Error fetching meal standard: {str(e)}")
    
    # Add meal type context for better comments
    meal_type_context = ""
    if meal_standard:
        meal_type_context = f"""
        Thông tin về tiêu chuẩn dinh dưỡng cho bữa {meal_type}:
        - Calo: {meal_standard.get('calories_percentage', 0)}% của nhu cầu hàng ngày
        - Protein: {meal_standard.get('protein_percentage', 0)}% của nhu cầu hàng ngày
        - Chất béo: {meal_standard.get('fat_percentage', 0)}% của nhu cầu hàng ngày
        - Carbohydrate: {meal_standard.get('carb_percentage', 0)}% của nhu cầu hàng ngày
        - Chất xơ: {meal_standard.get('fiber_percentage', 0)}% của nhu cầu hàng ngày
        """
    
    # Create prompt for Gemini API
    prompt = f"""
    Bạn là một chuyên gia dinh dưỡng. Tôi muốn bạn tạo đánh giá ngắn gọn về bữa ăn dựa trên sự so sánh dinh dưỡng với mục tiêu của người dùng.
    
    Đây là các thông tin chênh lệch giữa bữa ăn và mục tiêu của người dùng:
    - Loại bữa ăn: {meal_type}
    - Calo: {diff_calories} (âm nghĩa là thiếu, dương nghĩa là thừa)
    - Protein: {diff_protein}g (âm nghĩa là thiếu, dương nghĩa là thừa)
    - Chất béo: {diff_fat}g (âm nghĩa là thiếu, dương nghĩa là thừa)
    - Carbohydrate: {diff_carb}g (âm nghĩa là thiếu, dương nghĩa là thừa)
    - Chất xơ: {diff_fiber}g (âm nghĩa là thiếu, dương nghĩa là thừa)
    
    {meal_type_context}
    
    Tạo nhận xét ngắn gọn bằng tiếng Việt cho từng loại dinh dưỡng (protein, chất béo, carbohydrate, chất xơ, và calo), có tính đến tiêu chuẩn dinh dưỡng của loại bữa ăn này.
    Mỗi nhận xét chỉ 1-2 câu súc tích, đề cập đến:
    1. Đánh giá chênh lệch
    2. Gợi ý đơn giản để cải thiện (nếu cần)
    
    Phản hồi theo định dạng JSON chỉ bao gồm các trường sau:
    {
      "protein_comment": "Nhận xét ngắn gọn về protein...",
      "fat_comment": "Nhận xét ngắn gọn về chất béo...",
      "carb_comment": "Nhận xét ngắn gọn về carbohydrate...",
      "fiber_comment": "Nhận xét ngắn gọn về chất xơ...",
      "calories_comment": "Nhận xét ngắn gọn về calo..."
    }
    """
    
    try:
        # Asynchronously call Gemini API
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
        
        # Extract JSON response
        content = response.text
        print(f"Raw Gemini response: {content}")  # Debug print
        
        # Process the response to ensure it's a clean JSON
        # Remove any markdown formatting if exists
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Convert to dict using json.loads instead of eval for better safety
        try:
            # First try with json.loads for safer parsing
            result = json.loads(content)
            print(f"Parsed result: {result}")  # Debug print
            
            # Ensure all required fields are present
            required_fields = ["protein_comment", "fat_comment", "carb_comment", "fiber_comment", "calories_comment"]
            for field in required_fields:
                if field not in result:
                    result[field] = generate_fallback_comment(field, comparison)
            return result
        except json.JSONDecodeError:
            # If json.loads fails, try with eval as fallback
            try:
                result = eval(content)
                # Ensure all required fields are present
                required_fields = ["protein_comment", "fat_comment", "carb_comment", "fiber_comment", "calories_comment"]
                for field in required_fields:
                    if field not in result:
                        result[field] = generate_fallback_comment(field, comparison)
                return result
            except:
                print(f"Failed to parse with both json.loads and eval: {content}")  # Debug print
                # Fallback to default comments if JSON parsing fails
                return generate_fallback_comments(comparison)
    
    except Exception as e:
        print(f"Error calling Gemini API: {str(e)}")
        # Fallback to default comments
        return generate_fallback_comments(comparison)

def generate_fallback_comments(comparison: Dict[str, Any]) -> Dict[str, str]:
    """Generate fallback comments if Gemini API call fails"""
    return {
        "protein_comment": generate_fallback_comment("protein_comment", comparison),
        "fat_comment": generate_fallback_comment("fat_comment", comparison),
        "carb_comment": generate_fallback_comment("carb_comment", comparison),
        "fiber_comment": generate_fallback_comment("fiber_comment", comparison),
        "calories_comment": generate_fallback_comment("calories_comment", comparison)
    }

def generate_fallback_comment(comment_type: str, comparison: Dict[str, Any]) -> str:
    """Generate a fallback comment for a specific nutrient type"""
    nutrient_name = comment_type.split("_")[0]
    diff_key = f"diff_{nutrient_name}"
    
    if diff_key == "diff_calories":
        key = "diff_calories"
    else:
        key = diff_key
    
    diff_value = comparison.get(key, 0)
    
    if abs(diff_value) < 5:
        return f"Lượng {nutrient_name} của bạn cân đối tốt với mục tiêu. Hãy duy trì chế độ ăn này."
    elif diff_value > 20:
        return f"Lượng {nutrient_name} của bạn cao hơn đáng kể so với mục tiêu. Cân nhắc giảm các thực phẩm giàu {nutrient_name}."
    elif diff_value > 10:
        return f"Lượng {nutrient_name} của bạn cao hơn khá nhiều so với mục tiêu. Có thể điều chỉnh bằng cách giảm nhẹ các thực phẩm giàu {nutrient_name}."
    elif diff_value < -20:
        return f"Lượng {nutrient_name} của bạn thấp hơn đáng kể so với mục tiêu. Hãy bổ sung thêm các thực phẩm giàu {nutrient_name}."
    elif diff_value < -10:
        return f"Lượng {nutrient_name} của bạn thấp hơn khá nhiều so với mục tiêu. Cần bổ sung thêm một ít thực phẩm giàu {nutrient_name}."
    else:
        return f"Lượng {nutrient_name} của bạn chỉ chênh lệch nhẹ so với mục tiêu. Không cần điều chỉnh nhiều."

async def generate_advice(comparison: Dict[str, Any], food: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate detailed advice using Google's Gemini API based on comparison data
    
    Args:
        comparison: Dictionary containing nutrition comparison data
        food: Dictionary containing food data
        
    Returns:
        Dictionary with detailed advice
    """
    # Import here to avoid circular imports
    from src.config.database import meal_type_standards_collection
    
    diff_calories = comparison.get("diff_calories", 0)
    diff_protein = comparison.get("diff_protein", 0)
    diff_fat = comparison.get("diff_fat", 0)
    diff_carb = comparison.get("diff_carb", 0)
    diff_fiber = comparison.get("diff_fiber", 0)
    food_name = food.get("name", "món ăn")
    meal_type = food.get("meal_type", "lunch")
    
    # Get meal type standard for context
    meal_standard = None
    if meal_type:
        try:
            meal_standard = await meal_type_standards_collection.find_one({"meal_type": meal_type})
        except Exception as e:
            print(f"Error fetching meal standard: {str(e)}")
    
    # Add meal type context for better advice
    meal_type_context = ""
    if meal_standard:
        meal_type_context = f"""
        Thông tin về tiêu chuẩn dinh dưỡng cho bữa {meal_type}:
        - Calo: {meal_standard.get('calories_percentage', 0)}% của nhu cầu hàng ngày
        - Protein: {meal_standard.get('protein_percentage', 0)}% của nhu cầu hàng ngày
        - Chất béo: {meal_standard.get('fat_percentage', 0)}% của nhu cầu hàng ngày
        - Carbohydrate: {meal_standard.get('carb_percentage', 0)}% của nhu cầu hàng ngày
        - Chất xơ: {meal_standard.get('fiber_percentage', 0)}% của nhu cầu hàng ngày
        - Mô tả: {meal_standard.get('description', 'Không có mô tả')}
        """
    
    # Get ingredients list as string
    ingredients = []
    for ingredient in food.get("ingredients", []):
        if isinstance(ingredient, dict) and "name" in ingredient:
            ingredients.append(ingredient["name"])
        elif isinstance(ingredient, dict) and "ingredient_id" in ingredient:
            # Đối với trường hợp ingredient chỉ có ingredient_id
            ingredients.append("Thành phần " + str(len(ingredients) + 1))
    
    ingredients_str = ", ".join(ingredients) if ingredients else "không có thông tin chi tiết"
    
    # Create prompt for Gemini API
    prompt = f"""
    Bạn là một chuyên gia dinh dưỡng hàng đầu. Tôi muốn bạn tạo lời khuyên chi tiết cho bữa ăn dựa trên sự so sánh dinh dưỡng với mục tiêu của người dùng.
    
    Thông tin về món ăn:
    - Tên món: {food_name}
    - Loại bữa ăn: {meal_type}
    - Thành phần: {ingredients_str}
    
    Đây là các thông tin chênh lệch giữa bữa ăn và mục tiêu của người dùng:
    - Calo: {diff_calories} (âm nghĩa là thiếu, dương nghĩa là thừa)
    - Protein: {diff_protein}g (âm nghĩa là thiếu, dương nghĩa là thừa)
    - Chất béo: {diff_fat}g (âm nghĩa là thiếu, dương nghĩa là thừa)
    - Carbohydrate: {diff_carb}g (âm nghĩa là thiếu, dương nghĩa là thừa)
    - Chất xơ: {diff_fiber}g (âm nghĩa là thiếu, dương nghĩa là thừa)
    
    {meal_type_context}
    
    Tạo lời khuyên chi tiết bao gồm (có tính đến đặc thù của loại bữa ăn):
    1. Khuyến nghị cụ thể về cách cải thiện bữa ăn này dựa trên tiêu chuẩn của bữa {meal_type}
    2. Đề xuất thay thế một số nguyên liệu để cân bằng dinh dưỡng tốt hơn
    3. Mẹo dinh dưỡng thực tế và chi tiết dành riêng cho bữa {meal_type}
    
    Phản hồi theo định dạng JSON chỉ bao gồm các trường sau:
    {
      "recommendations": ["Khuyến nghị 1", "Khuyến nghị 2", "Khuyến nghị 3"],
      "substitutions": [
        {
          "original": "Nguyên liệu gốc",
          "substitute": "Nguyên liệu thay thế",
          "benefit": "Lợi ích cụ thể với số liệu dinh dưỡng"
        }
      ],
      "tips": ["Mẹo 1", "Mẹo 2", "Mẹo 3"]
    }
    """
    
    try:
        # Asynchronously call Gemini API
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
        
        # Extract JSON response
        content = response.text
        print(f"Raw Gemini advice response: {content}")  # Debug print
        
        # Process the response to ensure it's a clean JSON
        # Remove any markdown formatting if exists
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Convert to dict using json.loads for safer handling
        try:
            # First try with json.loads
            result = json.loads(content)
            print(f"Parsed advice result: {result}")  # Debug print
            
            # Ensure all required fields are present
            required_fields = ["recommendations", "substitutions", "tips"]
            for field in required_fields:
                if field not in result:
                    if field == "recommendations":
                        result[field] = ["Cân bằng chế độ ăn để đạt được mục tiêu dinh dưỡng của bạn."]
                    elif field == "substitutions":
                        result[field] = [{"original": "Thực phẩm hiện tại", "substitute": "Lựa chọn cân bằng hơn", "benefit": "Cải thiện hồ sơ dinh dưỡng"}]
                    elif field == "tips":
                        result[field] = ["Duy trì chế độ ăn đa dạng và cân bằng."]
            
            return result
        except json.JSONDecodeError:
            # If json.loads fails, try with eval as fallback
            try:
                result = eval(content)
                # Ensure all required fields are present
                required_fields = ["recommendations", "substitutions", "tips"]
                for field in required_fields:
                    if field not in result:
                        if field == "recommendations":
                            result[field] = ["Cân bằng chế độ ăn để đạt được mục tiêu dinh dưỡng của bạn."]
                        elif field == "substitutions":
                            result[field] = [{"original": "Thực phẩm hiện tại", "substitute": "Lựa chọn cân bằng hơn", "benefit": "Cải thiện hồ sơ dinh dưỡng"}]
                        elif field == "tips":
                            result[field] = ["Duy trì chế độ ăn đa dạng và cân bằng."]
                
                return result
            except Exception as eval_error:
                print(f"Failed to parse with both json.loads and eval: {content}")
                print(f"Eval error: {str(eval_error)}")
                # Fallback to default advice if JSON parsing fails
                return generate_fallback_advice(comparison, food)
    
    except Exception as e:
        print(f"Error calling Gemini API for advice: {str(e)}")
        # Fallback to default advice
        return generate_fallback_advice(comparison, food)

def generate_fallback_advice(comparison: Dict[str, Any], food: Dict[str, Any]) -> Dict[str, Any]:
    """Generate fallback advice if Gemini API call fails"""
    from src.services.database import generate_recommendations, generate_substitutions, generate_tips
    
    return {
        "recommendations": generate_recommendations(comparison),
        "substitutions": generate_substitutions(food),
        "tips": generate_tips(comparison)
    }

async def generate_piggy_advice(
    advice_type: str,
    item_id: str,
    comparison_id: Optional[str] = None,
    nutrition_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate personalized advice from Piggy character based on ingredients, meals, or nutritional differences
    
    Args:
        advice_type: Type of advice (ingredient, meal, nutrition_difference)
        item_id: ID of the ingredient or meal
        comparison_id: ID of the nutrition comparison (required for nutrition_difference type)
        nutrition_type: Type of nutrition (protein, fat, carb, fiber, calories)
        
    Returns:
        Dictionary with Piggy's advice and image URL
    """
    try:
        # Import here to avoid circular imports
        from src.config.database import (
            ingredients_collection, foods_collection, 
            nutrition_comparisons_collection, nutrition_reviews_collection
        )
        from bson import ObjectId
        
        # Default Piggy image URL
        piggy_image_url = "https://example.com/images/piggy_character.png"
        
        if advice_type == "ingredient":
            # Get ingredient information
            ingredient = await ingredients_collection.find_one({"_id": ObjectId(item_id)})
            if not ingredient:
                return {
                    "advice": "Không tìm thấy!",
                    "image_url": piggy_image_url
                }
            
            # Create prompt for Gemini API
            prompt = f"""
            Bạn là Piggy, một chú heo nhỏ dễ thương đóng vai trò là chuyên gia dinh dưỡng trong ứng dụng theo dõi chế độ ăn. Hãy nói chuyện theo nhân vật, giọng điệu thân thiện, vui vẻ.
            
            Thông tin về nguyên liệu:
            - Tên: {ingredient.get("name", "không có tên")}
            - Hàm lượng protein: {ingredient.get("protein", 0)}g/100g
            - Hàm lượng chất béo: {ingredient.get("fat", 0)}g/100g
            - Hàm lượng carbohydrate: {ingredient.get("carb", 0)}g/100g
            - Hàm lượng chất xơ: {ingredient.get("fiber", 0)}g/100g
            - Calo: {ingredient.get("calories", 0)} kcal/100g
            
            Tạo một câu ngắn gọn 3-7 từ có giọng điệu của Piggy về nguyên liệu này. Chỉ nói một câu cực kỳ ngắn gọn như "Protein tuyệt vời đó!" hoặc "Nhiều chất xơ nè!".
            
            Đảm bảo câu nói rất ngắn gọn (3-7 từ), dễ thương và trực quan.
            """
            
        elif advice_type == "meal":
            # Get meal information
            food = await foods_collection.find_one({"_id": ObjectId(item_id)})
            if not food:
                return {
                    "advice": "Không tìm thấy!",
                    "image_url": piggy_image_url
                }
            
            # Extract key nutritional information
            meal_name = food.get("name", "món ăn không tên")
            meal_type = food.get("meal_type", "không xác định")
            total_calories = food.get("total_calories", 0)
            total_protein = food.get("total_protein", 0)
            total_fat = food.get("total_fat", 0)
            total_carb = food.get("total_carb", 0)
            total_fiber = food.get("total_fiber", 0)
            
            # Create prompt for Gemini API
            prompt = f"""
            Bạn là Piggy, một chú heo nhỏ dễ thương đóng vai trò là chuyên gia dinh dưỡng trong ứng dụng theo dõi chế độ ăn. Hãy nói chuyện theo nhân vật, giọng điệu thân thiện, vui vẻ.
            
            Thông tin về món ăn:
            - Tên: {meal_name}
            - Loại bữa ăn: {meal_type}
            - Tổng calo: {total_calories} kcal
            - Tổng protein: {total_protein}g
            - Tổng chất béo: {total_fat}g
            - Tổng carbohydrate: {total_carb}g
            - Tổng chất xơ: {total_fiber}g
            
            Tạo một câu ngắn gọn 3-7 từ có giọng điệu của Piggy về món ăn này. Chỉ nói một câu cực kỳ ngắn gọn như "Đủ dinh dưỡng nè!" hoặc "Cân bằng tuyệt vời!".
            
            Đảm bảo câu nói rất ngắn gọn (3-7 từ), dễ thương và trực quan.
            """
            
        elif advice_type == "nutrition_difference":
            if not comparison_id or not nutrition_type:
                return {
                    "advice": "Thiếu thông tin!",
                    "image_url": piggy_image_url
                }
            
            # Get comparison and review information
            comparison = await nutrition_comparisons_collection.find_one({"_id": ObjectId(comparison_id)})
            review = await nutrition_reviews_collection.find_one({"comparison_id": comparison_id})
            
            if not comparison or not review:
                return {
                    "advice": "Không có dữ liệu!",
                    "image_url": piggy_image_url
                }
            
            # Get the appropriate comment based on nutrition type
            nutrition_comment = ""
            if nutrition_type == "protein":
                nutrition_comment = review.get("protein_comment", "")
                diff_value = comparison.get("diff_protein", 0)
            elif nutrition_type == "fat":
                nutrition_comment = review.get("fat_comment", "")
                diff_value = comparison.get("diff_fat", 0)
            elif nutrition_type == "carb":
                nutrition_comment = review.get("carb_comment", "")
                diff_value = comparison.get("diff_carb", 0)
            elif nutrition_type == "fiber":
                nutrition_comment = review.get("fiber_comment", "")
                diff_value = comparison.get("diff_fiber", 0)
            elif nutrition_type == "calories":
                nutrition_comment = review.get("calories_comment", "")
                diff_value = comparison.get("diff_calories", 0)
            else:
                nutrition_comment = "Không có thông tin"
                diff_value = 0
            
            # Create a short prompt for short response
            prompt = f"""
            Bạn là Piggy, một chú heo nhỏ dễ thương đóng vai trò là chuyên gia dinh dưỡng. Hãy nói chuyện theo nhân vật, giọng điệu thân thiện, vui vẻ.
            
            Thông tin về chênh lệch dinh dưỡng:
            - Loại dinh dưỡng: {nutrition_type}
            - Giá trị chênh lệch: {diff_value} ({nutrition_type})
            
            Tạo một câu ngắn gọn 3-7 từ có giọng điệu của Piggy về chênh lệch dinh dưỡng này. Ví dụ:
            - Nếu thiếu protein: "Thêm thịt nha!"
            - Nếu thừa calo: "Hơi nhiều calo rồi!"
            - Nếu thiếu chất xơ: "Thiếu rau kìa!"
            
            Đảm bảo câu nói rất ngắn gọn (3-7 từ), dễ thương và trực quan.
            """
        else:
            return {
                "advice": "Không hỗ trợ loại này!",
                "image_url": piggy_image_url
            }
        
        # Call Gemini API
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: model.generate_content(prompt))
        
        # Extract text response
        advice = response.text.strip()
        
        # Ensure the advice is not empty and not too long
        if not advice or len(advice.split()) > 7:
            # For ingredient advice
            if advice_type == "ingredient":
                highest_nutrient = "protein"
                highest_value = 0
                
                if "protein" in ingredient:
                    highest_nutrient = "protein"
                    highest_value = ingredient.get("protein", 0)
                
                if "carb" in ingredient and ingredient.get("carb", 0) > highest_value:
                    highest_nutrient = "carb"
                    highest_value = ingredient.get("carb", 0)
                
                if "fat" in ingredient and ingredient.get("fat", 0) > highest_value:
                    highest_nutrient = "fat"
                    highest_value = ingredient.get("fat", 0)
                    
                fallback_phrases = {
                    "protein": "Protein tuyệt vời đó!",
                    "carb": "Năng lượng dồi dào nè!",
                    "fat": "Béo tốt cho sức khỏe!"
                }
                
                advice = fallback_phrases.get(highest_nutrient, "Ngon lắm đó!")
            
            # For meal advice
            elif advice_type == "meal":
                if comparison and "diff_calories" in comparison:
                    if comparison["diff_calories"] > 100:
                        advice = "Hơi nhiều calo nè!"
                    elif comparison["diff_calories"] < -100:
                        advice = "Thêm chút năng lượng!"
                    else:
                        advice = "Cân đối tốt đó!"
                else:
                    advice = "Bữa ăn ngon đấy!"
            
            # For nutrition difference advice
            elif advice_type == "nutrition_difference":
                if diff_value > 10:
                    advice = f"Hơi nhiều {nutrition_type} rồi!"
                elif diff_value < -10:
                    advice = f"Thiếu {nutrition_type} kìa!"
                else:
                    advice = f"{nutrition_type.capitalize()} vừa đủ!"
            
            else:
                advice = "Ngon lắm đó!"
        
        return {
            "advice": advice,
            "image_url": piggy_image_url
        }
        
    except Exception as e:
        print(f"Error generating Piggy advice: {str(e)}")
        return {
            "advice": "Ngon lắm đó!",
            "image_url": "https://example.com/images/piggy_character.png"
        }