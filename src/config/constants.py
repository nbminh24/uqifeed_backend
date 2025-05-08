from typing import Dict, Any

# Nutrition Constants
CALORIE_DISTRIBUTION: Dict[str, float] = {
    "breakfast": 0.25,  # 25% of daily calories
    "lunch": 0.40,      # 40% of daily calories
    "dinner": 0.35,     # 35% of daily calories
    "snack": None,      # Not based on daily percentage
    "light_meal": None, # Not based on daily percentage
    "drinks": None      # Not based on daily percentage
}

MAX_CALORIES: Dict[str, int] = {
    "snack": 200,
    "light_meal": 250,
    "drinks_per_100ml": 20
}

MACRO_RATIOS: Dict[str, Dict[str, float]] = {
    "breakfast": {"carbs": 0.35, "protein": 0.30, "fat": 0.35},
    "lunch": {"carbs": 0.40, "protein": 0.30, "fat": 0.30},
    "dinner": {"carbs": 0.25, "protein": 0.35, "fat": 0.40},
    "snack": {"carbs": 0.45, "protein": 0.30, "fat": 0.25},
    "light_meal": {"carbs": 0.50, "protein": 0.40, "fat": 0.10},
    "drinks": {"max_calories_per_100ml": 20}
}

# Authentication Constants
MAX_LOGIN_ATTEMPTS = 5
LOGIN_TIMEOUT_MINUTES = 15
PASSWORD_MIN_LENGTH = 8
PASSWORD_REQUIREMENTS = {
    "min_length": 8,
    "require_uppercase": True,
    "require_lowercase": True,
    "require_digit": True,
    "require_special": True
}

# Cache Settings
CACHE_TTL = 300  # 5 minutes
CACHE_SIZE = 1000

# Database Settings
DB_MAX_POOL_SIZE = 50
DB_MIN_POOL_SIZE = 10
DB_MAX_IDLE_TIME_MS = 30000
DB_WAIT_QUEUE_TIMEOUT_MS = 10000

# File Upload Settings
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_FILE_TYPES = ["image/jpeg", "image/png", "image/gif"]

# Error Messages
ERROR_MESSAGES = {
    "invalid_credentials": "Invalid username or password",
    "user_not_found": "User not found",
    "invalid_token": "Invalid or expired token",
    "rate_limit_exceeded": "Too many attempts. Please try again later",
    "invalid_file_type": "Invalid file type. Allowed types: {types}",
    "file_too_large": "File size exceeds maximum limit of {size}MB",
    "db_operation_failed": "Database operation failed: {error}",
    "db_timeout": "Database operation timed out",
    "invalid_input": "Invalid input: {details}"
} 