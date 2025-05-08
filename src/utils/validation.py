from typing import Dict, Any, Tuple
import re
from datetime import datetime
from src.config.constants import PASSWORD_REQUIREMENTS, ERROR_MESSAGES

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength against requirements
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < PASSWORD_REQUIREMENTS["min_length"]:
        return False, f"Password must be at least {PASSWORD_REQUIREMENTS['min_length']} characters long"
    
    if PASSWORD_REQUIREMENTS["require_uppercase"] and not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if PASSWORD_REQUIREMENTS["require_lowercase"] and not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if PASSWORD_REQUIREMENTS["require_digit"] and not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    
    if PASSWORD_REQUIREMENTS["require_special"] and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    
    return True, ""

def validate_nutrition_values(calories: float, protein: float, fat: float, carb: float) -> Tuple[bool, str]:
    """
    Validate nutrition values are non-negative and within reasonable ranges
    
    Args:
        calories: Total calories
        protein: Protein in grams
        fat: Fat in grams
        carb: Carbohydrates in grams
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if any(value < 0 for value in [calories, protein, fat, carb]):
        return False, "Nutrition values cannot be negative"
    
    if calories > 10000:  # Reasonable maximum for a single meal
        return False, "Calories value seems unreasonably high"
    
    if protein > 500 or fat > 500 or carb > 1000:  # Reasonable maximums
        return False, "Macronutrient values seem unreasonably high"
    
    return True, ""

def validate_date_format(date_str: str) -> Tuple[bool, str]:
    """
    Validate date string format (YYYY-MM-DD)
    
    Args:
        date_str: Date string to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True, ""
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD"

def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email format
    
    Args:
        email: Email to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        return False, "Invalid email format"
    return True, ""

def validate_food_data(food_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate food data structure and values
    
    Args:
        food_data: Food data dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    required_fields = ["name", "total_calories", "ingredients"]
    
    # Check required fields
    for field in required_fields:
        if field not in food_data:
            return False, f"Missing required field: {field}"
    
    # Validate calories
    if not isinstance(food_data["total_calories"], (int, float)) or food_data["total_calories"] < 0:
        return False, "Invalid total calories value"
    
    # Validate ingredients
    if not isinstance(food_data.get("ingredients", []), list):
        return False, "Ingredients must be a list"
    
    # Validate each ingredient
    for ingredient in food_data["ingredients"]:
        if not isinstance(ingredient, dict):
            return False, "Each ingredient must be a dictionary"
        
        required_ingredient_fields = ["name", "quantity", "unit"]
        for field in required_ingredient_fields:
            if field not in ingredient:
                return False, f"Missing required field in ingredient: {field}"
    
    return True, "" 