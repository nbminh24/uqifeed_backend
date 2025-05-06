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
    Analyze this food image and identify all food items visible. 
    For each item provide:
    1. Name of the food
    2. A detailed description (3-5 sentences) that includes:
       - Information about ingredients
       - Natural science aspects (nutritional benefits, origin)
       - Flavor profile
       - Cultural significance or traditional preparation methods
    3. Estimated nutrition per 100g or standard serving:
       - Calories
       - Protein (g)
       - Carbs (g)
       - Fat (g)
    
    Example description: "Sò (clams) have a sweet and rich flavor, found in coastal waters worldwide. They're an excellent source of protein, vitamin B12, and minerals like zinc and iron. Clams are commonly steamed, grilled, or used in soups. In Vietnamese cuisine, they're often enjoyed in hot pot dishes or stir-fried with tamarind sauce, representing the country's rich seafood tradition."
    
    Format your response as a JSON list of objects, each with 'name', 'description', and 'estimated_nutrition' fields.
    Example:
    [
      {
        "name": "Apple",
        "description": "Apples are crisp and sweet fruits with numerous health benefits. They contain dietary fiber, particularly pectin, which aids digestion and helps regulate blood sugar levels. The skin contains quercetin, a flavonoid with antioxidant properties. In many cultures, apples symbolize knowledge and are used in numerous desserts like pies and tarts.",
        "estimated_nutrition": {
          "calories": 52,
          "protein": 0.3,
          "carbs": 14,
          "fat": 0.2
        }
      },
      ...
    ]
    """
    
    try:
        # Generate content
        response = model.generate_content([prompt, image])
        
        # Extract the text response
        text_response = response.text
        
        # Process the response to extract food items
        # (In production, you'd use proper JSON parsing with error handling)
        # This is a simplified example
        
        import json
        import re
        
        # Try to find JSON content in the response
        json_match = re.search(r'\[\s*\{.*\}\s*\]', text_response, re.DOTALL)
        
        if json_match:
            json_str = json_match.group(0)
            try:
                food_items_data = json.loads(json_str)
                
                # Convert to FoodItem objects
                food_items = []
                for item_data in food_items_data:
                    try:
                        # Create nutrition info
                        nutrition_data = item_data.get("estimated_nutrition", {})
                        
                        food_item = FoodItem(
                            name=item_data["name"],
                            description=item_data.get("description", ""),
                            confidence=0.8,  # Gemini doesn't provide confidence scores
                            estimated_nutrition={
                                "calories": nutrition_data.get("calories", 0),
                                "protein": nutrition_data.get("protein", 0),
                                "carbs": nutrition_data.get("carbs", 0),
                                "fat": nutrition_data.get("fat", 0)
                            }
                        )
                        food_items.append(food_item)
                    except Exception as e:
                        # Skip items with errors
                        continue
                
                return food_items
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                pass
        
        # If JSON parsing fails, extract basic food names
        food_names = extract_food_names_from_text(text_response)
        return [FoodItem(name=name) for name in food_names]
        
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