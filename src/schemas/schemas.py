# Import các schema từ các module con để tránh trùng lặp
from src.schemas.user.user_schema import UserCreate, UserResponse
from src.schemas.user.profile_schema import (
    Gender,
    ActivityLevel,
    WeightGoal,
    DietType,
    AdditionalGoal,
    ProfileNutritionCreate,
    ProfileNutritionUpdate,
    ProfileNutritionResponse,
    ProgressProjection
)
from src.schemas.food.food_schema import (
    MongoBaseModel,
    MealTypeEnum,
    FoodCategory,
    IngredientBase,
    IngredientCreate,
    IngredientResponse,
    FoodIngredientBase,
    FoodBase,
    FoodCreate,
    FoodUpdate,
    FoodResponse,
    FoodItem,
    FoodDetectionResponse,
    FoodImageUpload,
    IngredientRecognition,
    FoodRecognitionResponse,
    NutritionInfo,
    MealTypeNutritionalStandards
)
from src.schemas.dish.dish_schema import (
    DishBase,
    DishCreate,
    DishResponse,
    DishUpdate,
    DishRequest
)
from src.schemas.notification.notification_schema import (
    NotificationBase,
    ReminderTimes,
    NotificationSettingsBase,
    NotificationResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdate
)
from src.schemas.nutrition.nutrition_schema import (
    NutritionTarget,
    NutritionTargetResponse,
    NutritionTargetBase,
    NutritionComparisonBase,
    NutritionReviewBase,
    SubstitutionItem,
    AdviseBase,
    DailyReportBase,
    WeeklyReportBase,
    WeeklyIngredientUsageBase
)
from src.schemas.calorie.calorie_schema import (
    MeasurementUnitBase,
    ChartTypeEnum,
    WeeklyReportCommentBase
)

# Tất cả các schema được export
__all__ = [
    # User schemas
    "UserCreate", "UserResponse",
    
    # Profile schemas
    "Gender", "ActivityLevel", "WeightGoal", "DietType", "AdditionalGoal",
    "ProfileNutritionCreate", "ProfileNutritionUpdate", "ProfileNutritionResponse",
    "ProgressProjection",
    
    # Base MongoDB model
    "MongoBaseModel",
    
    # Enums
    "MealTypeEnum", "FoodCategory", "ChartTypeEnum",
    
    # Nutrition Information Schemas
    "NutritionInfo",
    
    # Ingredient Schemas
    "IngredientBase", "IngredientCreate", "IngredientResponse", "FoodIngredientBase",
    
    # Food Base Schemas
    "FoodBase", "FoodCreate", "FoodUpdate", "FoodResponse",
    
    # Dish Schemas
    "DishBase", "DishCreate", "DishResponse", "DishUpdate",
    
    # Food Detection and Recognition Schemas
    "FoodItem", "FoodDetectionResponse", "FoodImageUpload", "IngredientRecognition", 
    "FoodRecognitionResponse",
    
    # API Request Schemas
    "DishRequest",
    
    # Nutrition schemas
    "NutritionTarget", "NutritionTargetResponse", "NutritionTargetBase",
    "NutritionComparisonBase", "NutritionReviewBase",
    
    # Report schemas
    "DailyReportBase", "WeeklyReportBase", "WeeklyIngredientUsageBase",
    "WeeklyReportCommentBase", "SubstitutionItem", "AdviseBase",
    
    # Notification schemas
    "NotificationBase", "NotificationResponse", "NotificationSettingsBase",
    "NotificationSettingsResponse", "NotificationSettingsUpdate", "ReminderTimes",
    
    # Measurement Unit schemas
    "MeasurementUnitBase",
    
    # Meal Type standards
    "MealTypeNutritionalStandards"
]