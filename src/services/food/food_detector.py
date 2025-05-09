import os
import base64
from datetime import datetime
from typing import List, Dict, Any, Optional
import google.generativeai as genai
import PIL.Image

from src.schemas.food.food_schema import FoodItem, FoodCategory
import config

# Configure API key for Gemini Vision
if hasattr(config, 'GEMINI_API_KEY'):
    genai.configure(api_key=config.GEMINI_API_KEY)

async def detect_food_from_image(image_path: str, model: str = "gemini-pro-vision") -> List[FoodItem]:
    """
    Detect food items in an image using AI vision models
    
    Args:
        image_path: Path to the image file
        model: AI model to use
    
    Returns:
        List[FoodItem]: List of detected food items
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Different detection logic based on selected model
    if model == "gemini-pro-vision":
        return await detect_food_with_gemini(image_path)
    else:
        raise ValueError(f"Unsupported model: {model}")

async def detect_food_with_gemini(image_path: str) -> List[FoodItem]:
    """
    Use Google's Gemini Pro Vision model to detect food in an image
    
    Args:
        image_path: Path to the image file
    
    Returns:
        List[FoodItem]: List of detected food items with estimated nutrition and detailed descriptions
    """
    # Load the image
    image = PIL.Image.open(image_path)
    
    # Initialize Gemini model
    model = genai.GenerativeModel('gemini-pro-vision')
    
    # Prompt for food detection with detailed descriptions and nutrition estimation
    prompt = """
    Analyze this food image and identify the dish and its ingredients. 
    
    For the dish:
    1. Name of the dish
    2. A detailed description (3-5 sentences) that includes:
       - Cultural origin and significance
       - Flavor profile
       - Traditional preparation methods
    3. List of ingredients with detailed information for each, including:
       - Name of the ingredient
       - Estimated quantity and unit (g, ml, etc.)
       - Nutritional value per quantity used:
         * Protein (g)
         * Fat (g)
         * Carbs (g)
         * Fiber (g)
         * Calories
       - "Did You Know" fact: Write exactly 3 sentences about the ingredient:
         * First sentence: A scientific/botanical description
         * Second sentence: Nutritional benefits or properties
         * Third sentence: Cultural significance or culinary uses across different cuisines
    4. Overall nutritional information of the dish:
       - Total calories
       - Total protein (g)
       - Total fat (g)
       - Total carbs (g)
       - Total fiber (g)
    5. Health advice (write exactly 3 paragraphs):
       - First paragraph: Detailed nutritional analysis including:
         * Main nutrients provided
         * Potential health concerns (e.g., high sodium, saturated fat)
         * Impact on specific health conditions if any
       - Second paragraph: Specific suggestions for making the dish healthier:
         * Ingredient substitutions
         * Cooking method modifications
         * Portion control recommendations
       - Third paragraph: Best practices for consumption:
         * Ideal serving size
         * Recommended frequency
         * Complementary foods to balance nutrition
         * Tips for digestion and nutrient absorption
    
    Format your response as a JSON with 'food_name', 'description', 'ingredients' (array), 'total_calories', 'total_protein', 'total_fat', 'total_carb', 'total_fiber', and 'health_advice' fields.
    Each ingredient should have 'name', 'quantity', 'unit', 'protein', 'fat', 'carb', 'fiber', 'calories', and 'did_you_know' fields.
    The 'health_advice' field should be an object with 'benefits', 'improvements', and 'consumption' fields.
    
    Example:
    {
      "food_name": "Cheese Pizza",
      "description": "A classic Italian dish featuring a thin crust topped with tomato sauce and melted cheese. The combination of crispy crust, tangy sauce, and gooey cheese creates a satisfying comfort food that has become popular worldwide.",
      "ingredients": [
        {
          "name": "Pizza Dough",
          "quantity": 150,
          "unit": "g",
          "protein": 4.5,
          "fat": 1.2,
          "carb": 35,
          "fiber": 2.1,
          "calories": 170,
          "did_you_know": "Pizza dough is made from wheat flour, water, yeast, and salt, creating a versatile base that can be thin and crispy or thick and chewy. The fermentation process breaks down complex carbohydrates, making them easier to digest. From Neapolitan to New York style, different regions have developed unique dough recipes and techniques."
        },
        {
          "name": "Mozzarella Cheese",
          "quantity": 100,
          "unit": "g",
          "protein": 22,
          "fat": 22,
          "carb": 2.2,
          "fiber": 0,
          "calories": 280,
          "did_you_know": "Mozzarella is a semi-soft Italian cheese made from buffalo or cow's milk, known for its stretchy texture when melted. Rich in calcium and protein, it provides essential nutrients for bone health and muscle maintenance. Originally from southern Italy, mozzarella is now a key ingredient in many global cuisines, particularly in pizza and pasta dishes."
        }
      ],
      "total_calories": 450,
      "total_protein": 26.5,
      "total_fat": 23.2,
      "total_carb": 37.2,
      "total_fiber": 2.1,
      "health_advice": {
        "benefits": "Pizza provides a good balance of carbohydrates, protein, and fat, making it a satisfying meal. The tomato sauce contributes antioxidants like lycopene, while the cheese offers calcium and protein. However, the combination of refined flour, cheese, and processed meats can be high in sodium, saturated fat, and calories, which may impact heart health and weight management if consumed frequently.",
        "improvements": "To make pizza healthier, opt for a thin whole-grain crust to increase fiber content. Use part-skim mozzarella or a blend of reduced-fat cheeses to lower saturated fat. Add plenty of vegetables like bell peppers, mushrooms, and spinach for added nutrients and fiber. Consider using lean protein sources like grilled chicken instead of processed meats, and go easy on the cheese to reduce calorie and fat content.",
        "consumption": "A standard serving of pizza is typically 1-2 slices (about 1/6 of a medium pizza). For optimal health, enjoy pizza as an occasional treat rather than a regular meal. Pair it with a side salad to increase vegetable intake and fiber content. To aid digestion, consider having a small portion of fresh fruit after the meal to help balance the meal's acidity and provide additional nutrients."
      }
    }
    """
    
    try:
        # Generate content
        response = model.generate_content([prompt, image])
        
        # Extract the text response
        text_response = response.text
        
        # Process the response to extract food information
        import json
        import re
        
        # Try to find JSON content in the response (object format)
        json_match = re.search(r'\{[\s\S]*\}', text_response, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(0)
            try:
                food_data = json.loads(json_str)
                
                # Prepare data according to FoodRecognitionResponse schema
                food_recognition = {
                    "food_name": food_data.get("food_name", "Unknown Food"),
                    "meal_type": "lunch",  # Default value, can be overridden later
                    "ingredients": [],
                    "total_calories": food_data.get("total_calories", 0),
                    "total_protein": food_data.get("total_protein", 0),
                    "total_fat": food_data.get("total_fat", 0),
                    "total_carb": food_data.get("total_carb", 0),
                    "total_fiber": food_data.get("total_fiber", 0),
                    "health_advice": food_data.get("health_advice", {
                        "benefits": "No health advice available.",
                        "improvements": "No improvement suggestions available.",
                        "consumption": "No consumption advice available."
                    })
                }
                
                # Process ingredients
                for ing_data in food_data.get("ingredients", []):
                    ingredient = {
                        "name": ing_data.get("name", "Unknown"),
                        "quantity": ing_data.get("quantity", 0),
                        "unit": ing_data.get("unit", "g"),
                        "protein": ing_data.get("protein", 0),
                        "fat": ing_data.get("fat", 0),
                        "carb": ing_data.get("carb", 0),
                        "fiber": ing_data.get("fiber", 0),
                        "calories": ing_data.get("calories", 0),
                        "did_you_know": ing_data.get("did_you_know", "")
                    }
                    food_recognition["ingredients"].append(ingredient)
                
                return food_recognition
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {str(e)}")
                print(f"Response text: {text_response}")
                # Fall through to fallback method
        
        # Fallback: If proper JSON parsing fails, return basic food item
        food_names = extract_food_names_from_text(text_response)
        if food_names:
            return {
                "food_name": food_names[0],
                "meal_type": "lunch",
                "ingredients": [],
                "total_calories": 0,
                "total_protein": 0,
                "total_fat": 0,
                "total_carb": 0,
                "total_fiber": 0,
                "health_advice": {
                    "benefits": "No health advice available.",
                    "improvements": "No improvement suggestions available.",
                    "consumption": "No consumption advice available."
                }
            }
        else:
            return {
                "food_name": "Unknown Food",
                "meal_type": "lunch",
                "ingredients": [],
                "total_calories": 0,
                "total_protein": 0,
                "total_fat": 0,
                "total_carb": 0,
                "total_fiber": 0,
                "health_advice": {
                    "benefits": "No health advice available.",
                    "improvements": "No improvement suggestions available.",
                    "consumption": "No consumption advice available."
                }
            }
        
    except Exception as e:
        # Log the error and return empty list
        print(f"Error in Gemini food detection: {str(e)}")
        return []

def extract_food_names_from_text(text: str) -> List[str]:
    """
    Extract food names from text when JSON parsing fails
    
    Args:
        text: Text response from the model
    
    Returns:
        List[str]: List of food names
    """
    # Simple extraction based on common patterns
    import re
    
    # Look for food names after patterns like "1.", "Name:", "Food:"
    food_matches = re.findall(r'(?:(?:\d+[\.\):]|Name:|Food:)\s*([A-Za-z\s]+))', text)
    
    # Clean up and deduplicate
    foods = []
    for match in food_matches:
        food_name = match.strip()
        if food_name and food_name not in foods:
            foods.append(food_name)
    
    # If nothing found, split by newlines and look for capitalized words
    if not foods:
        for line in text.split('\n'):
            if line.strip() and line[0].isupper():
                food_name = line.split('(')[0].split('-')[0].strip()
                if 2 < len(food_name) < 30 and food_name not in foods:
                    foods.append(food_name)
    
    return foods