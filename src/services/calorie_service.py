from typing import Dict, List, Any
import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

# Configure the Gemini API if needed for AI advice
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

async def calculate_dish_calories(ingredients: List[Dict]) -> float:
    """
    Calculate calories for a dish based on its ingredients
    
    Args:
        ingredients: List of ingredient data with protein, fat, carbs, and amount
        
    Returns:
        Total calories for the dish
    """
    total_calories = 0
    for ingredient in ingredients:
        protein = ingredient.get("protein", 0) * ingredient.get("amount", 0) / 100
        fat = ingredient.get("fat", 0) * ingredient.get("amount", 0) / 100
        carbs = ingredient.get("carbs", 0) * ingredient.get("amount", 0) / 100
        
        # Calculate calories: 4 cal/g for protein and carbs, 9 cal/g for fat
        calories = (protein * 4) + (fat * 9) + (carbs * 4)
        total_calories += calories
    
    return total_calories

async def calculate_total_nutrition(ingredients: List[Dict]) -> Dict[str, float]:
    """
    Calculate total nutrition values for a list of ingredients
    
    Args:
        ingredients: List of ingredient data with protein, fat, carbs, and amount
        
    Returns:
        Dictionary with total protein, fat, and carbs
    """
    total_protein = 0
    total_fat = 0
    total_carbs = 0
    
    for ingredient in ingredients:
        protein = ingredient.get("protein", 0) * ingredient.get("amount", 0) / 100
        fat = ingredient.get("fat", 0) * ingredient.get("amount", 0) / 100
        carbs = ingredient.get("carbs", 0) * ingredient.get("amount", 0) / 100
        
        total_protein += protein
        total_fat += fat
        total_carbs += carbs
    
    return {
        "total_protein": total_protein,
        "total_fat": total_fat,
        "total_carbs": total_carbs
    }

async def calculate_meal_calories(dishes: List[Dict]) -> float:
    """
    Calculate total calories for a meal based on its dishes
    
    Args:
        dishes: List of dish data with protein, fat, carbs values
        
    Returns:
        Total calories for the meal
    """
    return await calculate_dish_calories(dishes)

async def generate_nutrition_advice(
    food_data: Dict[str, Any],
    target_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate nutrition advice using AI for a food compared to a target
    
    Args:
        food_data: Food nutritional information
        target_data: Target nutritional information
        
    Returns:
        Dictionary with advice and review information
    """
    try:
        # Calculate differences
        diff_calories = food_data["total_calories"] - target_data["target_calories"]
        
        # Convert target percentages to grams for comparison
        target_protein_grams = (target_data["target_protein"] / 100) * target_data["target_calories"] / 4
        target_fat_grams = (target_data["target_fat"] / 100) * target_data["target_calories"] / 9
        target_carb_grams = (target_data["target_carb"] / 100) * target_data["target_calories"] / 4
        
        diff_protein = food_data["total_protein"] - target_protein_grams
        diff_fat = food_data["total_fat"] - target_fat_grams
        diff_carb = food_data["total_carb"] - target_carb_grams
        diff_fiber = food_data["total_fiber"] - target_data["target_fiber"]
        
        # Determine if differences are significant
        calories_significant = abs(diff_calories) > 200
        protein_significant = abs(diff_protein) > 10
        fat_significant = abs(diff_fat) > 5
        carb_significant = abs(diff_carb) > 20
        fiber_significant = abs(diff_fiber) > 5
        
        # Generate review comments
        protein_comment = generate_nutrient_comment("protein", diff_protein, protein_significant)
        fat_comment = generate_nutrient_comment("fat", diff_fat, fat_significant)
        carb_comment = generate_nutrient_comment("carbohydrate", diff_carb, carb_significant)
        fiber_comment = generate_nutrient_comment("fiber", diff_fiber, fiber_significant)
        calories_comment = generate_nutrient_comment("calorie", diff_calories, calories_significant, is_calories=True)
        
        # Determine advice type based on overall assessment
        if (diff_calories > 300 or diff_fat > 10 or diff_carb > 30):
            advice_type = "reduce"
        elif (diff_calories < -300 or diff_protein < -15):
            advice_type = "how to improve"
        elif (abs(diff_calories) < 150 and abs(diff_protein) < 10 and abs(diff_fat) < 7 and abs(diff_carb) < 20):
            advice_type = "keep"
        else:
            advice_type = "how to improve"
        
        # Generate summary and advice
        summary = f"This meal is {get_meal_description(food_data, target_data)}"
        
        advice_text = generate_advice_text(
            food_data["name"],
            diff_calories,
            diff_protein,
            diff_fat,
            diff_carb,
            diff_fiber,
            advice_type
        )
        
        return {
            "review": {
                "protein_comment": protein_comment,
                "fat_comment": fat_comment,
                "carb_comment": carb_comment,
                "fiber_comment": fiber_comment,
                "calories_comment": calories_comment
            },
            "advice": {
                "advice_type": advice_type,
                "summary": summary,
                "advice_text": advice_text
            }
        }
    
    except Exception as e:
        print(f"Error generating nutrition advice: {e}")
        return {
            "review": {
                "protein_comment": "Unable to generate protein comment.",
                "fat_comment": "Unable to generate fat comment.",
                "carb_comment": "Unable to generate carb comment.",
                "fiber_comment": "Unable to generate fiber comment.",
                "calories_comment": "Unable to generate calories comment."
            },
            "advice": {
                "advice_type": "how to improve",
                "summary": "Unable to generate summary.",
                "advice_text": "Unable to generate advice text."
            }
        }

def generate_nutrient_comment(nutrient_type, diff, is_significant, is_calories=False):
    """
    Generate a comment about a nutrient based on the difference from target
    
    Args:
        nutrient_type: Type of nutrient (protein, fat, carb, fiber, calorie)
        diff: Difference from target
        is_significant: Whether the difference is significant
        is_calories: Whether the nutrient is calories
        
    Returns:
        Comment string
    """
    if not is_significant:
        return f"The {nutrient_type} content is appropriate for your nutritional goals."
    
    if is_calories:
        if diff > 0:
            return f"This meal provides {abs(diff):.0f} calories more than your target. Consider reducing portion size or choosing lower-calorie alternatives."
        else:
            return f"This meal provides {abs(diff):.0f} calories less than your target. You may need additional food to meet your daily calorie needs."
    else:
        if diff > 0:
            return f"This meal contains more {nutrient_type} than your nutritional target. You're getting {abs(diff):.1f}g extra {nutrient_type}."
        else:
            return f"This meal is low in {nutrient_type} compared to your nutritional target. You're getting {abs(diff):.1f}g less {nutrient_type} than optimal."

def get_meal_description(food_data, target_data):
    """
    Get an overall description of how well the meal matches the target
    
    Args:
        food_data: Food nutritional information
        target_data: Target nutritional information
        
    Returns:
        Description string
    """
    # Calculate percentage of daily calorie target
    calorie_percentage = (food_data["total_calories"] / target_data["target_calories"]) * 100
    
    if calorie_percentage < 20:
        return "a light snack that provides less than 20% of your daily calorie needs."
    elif calorie_percentage < 33:
        return "a moderate snack or small meal that provides roughly 25-30% of your daily calorie needs."
    elif calorie_percentage < 45:
        return "a substantial meal providing about 33-40% of your daily calorie needs."
    elif calorie_percentage < 60:
        return "a large meal providing about 50% of your daily calorie needs. Consider if this fits your meal pattern."
    else:
        return "a very large meal providing over 60% of your daily calorie needs. Consider dividing this into multiple meals."

def generate_advice_text(food_name, diff_calories, diff_protein, diff_fat, diff_carb, diff_fiber, advice_type):
    """
    Generate detailed advice text based on nutritional differences
    
    Args:
        food_name: Name of the food
        diff_calories: Calorie difference
        diff_protein: Protein difference
        diff_fat: Fat difference
        diff_carb: Carb difference
        diff_fiber: Fiber difference
        advice_type: Type of advice to generate
        
    Returns:
        Advice text string
    """
    if advice_type == "keep":
        return f"The nutritional profile of {food_name} is well-balanced and aligns with your nutritional goals. This is a good meal choice for your diet plan."
    
    elif advice_type == "reduce":
        advice = f"To better align {food_name} with your nutritional goals, consider the following adjustments:\n\n"
        
        if diff_calories > 200:
            advice += "- Reduce the portion size to lower the overall calorie content.\n"
        if diff_fat > 7:
            advice += "- Reduce high-fat ingredients or substitute with lower-fat alternatives.\n"
        if diff_carb > 20:
            advice += "- Reduce carbohydrate-rich components or replace with more vegetables.\n"
        if diff_protein < -10:
            advice += "- Add more protein-rich ingredients to better meet your protein requirements.\n"
        if diff_fiber < -5:
            advice += "- Add more fiber-rich ingredients like vegetables, fruits, or whole grains.\n"
        
        return advice
    
    elif advice_type == "how to improve":
        advice = f"To optimize {food_name} for your nutritional goals, consider these adjustments:\n\n"
        
        if diff_calories < -200:
            advice += "- Increase the portion size or add calorie-dense ingredients to meet your energy needs.\n"
        if diff_protein < -10:
            advice += "- Add more protein sources like lean meat, eggs, dairy, or plant-based proteins.\n"
        if diff_fat < -7:
            advice += "- Include healthy fat sources like avocado, nuts, seeds, or olive oil.\n"
        if diff_fiber < -5:
            advice += "- Add more fiber-rich foods like vegetables, fruits, legumes, or whole grains.\n"
        if diff_carb < -20:
            advice += "- Include more complex carbohydrates like whole grains, starchy vegetables, or fruits.\n"
        
        return advice
    
    else:  # "stop"
        return f"{food_name} contains significantly more calories and macronutrients than your daily targets. Consider replacing this meal with lighter alternatives or reducing the portion size substantially to align with your nutritional goals."