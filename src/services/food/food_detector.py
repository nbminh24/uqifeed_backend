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
    
    Example "Did You Know" fact format: 
    "Clams are a nutritious and flavorful shellfish often featured in both everyday meals and traditional dishes around the world. Naturally rich in protein, iron, and vitamin B12, they are commonly steamed, grilled, stir-fried, or added to soups for their sweet, briny taste. From Asian-style lemongrass steamed clams to Western clam chowder, they showcase a delicious blend of nutrition and cultural variety."
    
    Format your response as a JSON with 'food_name', 'description', 'ingredients' (array), 'total_calories', 'total_protein', 'total_fat', 'total_carb', and 'total_fiber' fields.
    Each ingredient should have 'name', 'quantity', 'unit', 'protein', 'fat', 'carb', 'fiber', 'calories', and 'did_you_know' fields.
    
    Example:
    {
      "food_name": "Vietnamese Pho",
      "description": "Pho is a traditional Vietnamese soup consisting of broth, rice noodles, herbs, and meat. It's known for its complex flavor profile balancing sweet, salty, citrus, and heat. The dish originated in northern Vietnam and became popular worldwide for its aromatic broth that's simmered for hours with spices.",
      "ingredients": [
        {
          "name": "Rice Noodles",
          "quantity": 100,
          "unit": "g",
          "protein": 2,
          "fat": 0.5,
          "carb": 24,
          "fiber": 0.9,
          "calories": 109,
          "did_you_know": "Rice noodles are made from rice flour and water, forming translucent, delicate strands with a tender texture when cooked. They are naturally gluten-free and low in fat, making them suitable for various dietary restrictions. From Vietnamese pho to Thai pad thai, rice noodles are a versatile staple in many Southeast Asian cuisines, adapting well to both stir-fries and soups."
        },
        {
          "name": "Beef Broth",
          "quantity": 350,
          "unit": "ml",
          "protein": 5.6,
          "fat": 2.1,
          "carb": 0.8,
          "fiber": 0,
          "calories": 44,
          "did_you_know": "Beef broth is made by simmering beef bones, meat, and vegetables in water to extract flavors, nutrients, and gelatin. Rich in collagen, amino acids, and minerals like calcium and magnesium, it may support joint health and improve gut barrier function. From French onion soup to Vietnamese pho, beef broth forms the flavor foundation of countless traditional dishes across global cuisines."
        }
      ],
      "total_calories": 320,
      "total_protein": 18,
      "total_fat": 7.8,
      "total_carb": 42,
      "total_fiber": 2.1
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
                    "total_fiber": food_data.get("total_fiber", 0)
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
                "total_fiber": 0
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
                "total_fiber": 0
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