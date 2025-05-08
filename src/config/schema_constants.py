from typing import Dict, Any

# Schema Validation Rules
SCHEMA_VALIDATION = {
    "user": {
        "email": {
            "type": "string",
            "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "min_length": 5,
            "max_length": 100
        },
        "password": {
            "type": "string",
            "min_length": 8,
            "max_length": 100
        },
        "name": {
            "type": "string",
            "min_length": 2,
            "max_length": 50
        },
        "age": {
            "type": "integer",
            "minimum": 13,
            "maximum": 120
        },
        "height": {
            "type": "number",
            "minimum": 100,
            "maximum": 250
        },
        "weight": {
            "type": "number",
            "minimum": 30,
            "maximum": 300
        }
    },
    "food": {
        "name": {
            "type": "string",
            "min_length": 2,
            "max_length": 100
        },
        "calories": {
            "type": "number",
            "minimum": 0,
            "maximum": 10000
        },
        "protein": {
            "type": "number",
            "minimum": 0,
            "maximum": 500
        },
        "fat": {
            "type": "number",
            "minimum": 0,
            "maximum": 500
        },
        "carb": {
            "type": "number",
            "minimum": 0,
            "maximum": 1000
        },
        "fiber": {
            "type": "number",
            "minimum": 0,
            "maximum": 100
        }
    },
    "meal": {
        "type": {
            "type": "string",
            "enum": ["breakfast", "lunch", "dinner", "snack", "light_meal", "drinks"]
        },
        "date": {
            "type": "string",
            "pattern": r"^\d{4}-\d{2}-\d{2}$"
        },
        "time": {
            "type": "string",
            "pattern": r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$"
        }
    }
}

# Database Indexes
DB_INDEXES = {
    "users": [
        {"email": 1, "unique": True},
        {"created_at": -1},
        {"is_active": 1}
    ],
    "foods": [
        {"user_id": 1, "created_at": -1},
        {"name": "text"},
        {"meal_type": 1, "eating_time": -1}
    ],
    "nutrition_targets": [
        {"user_id": 1, "unique": True},
        {"created_at": -1}
    ],
    "nutrition_comparisons": [
        {"user_id": 1, "created_at": -1},
        {"food_id": 1}
    ]
}

# Database Collections
COLLECTIONS = {
    "users": "users",
    "foods": "foods",
    "nutrition_targets": "nutrition_targets",
    "nutrition_comparisons": "nutrition_comparisons",
    "nutrition_reviews": "nutrition_reviews",
    "advises": "advises",
    "profiles": "profiles"
}

# API Response Messages
API_MESSAGES = {
    "success": {
        "create": "Created successfully",
        "update": "Updated successfully",
        "delete": "Deleted successfully",
        "get": "Retrieved successfully"
    },
    "error": {
        "not_found": "Resource not found",
        "invalid_input": "Invalid input data",
        "unauthorized": "Unauthorized access",
        "forbidden": "Access forbidden",
        "server_error": "Internal server error"
    }
}

# API Response Status Codes
STATUS_CODES = {
    "success": 200,
    "created": 201,
    "no_content": 204,
    "bad_request": 400,
    "unauthorized": 401,
    "forbidden": 403,
    "not_found": 404,
    "conflict": 409,
    "server_error": 500
} 