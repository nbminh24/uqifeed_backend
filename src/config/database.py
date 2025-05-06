from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient, IndexModel, ASCENDING, DESCENDING, TEXT
from pymongo.collection import Collection
from bson import ObjectId
import os
from dotenv import load_dotenv
import config
import asyncio
import logging
from datetime import datetime

# Get logger
from src.utils.error_handling import logger

load_dotenv()

# Database connection setup
client = AsyncIOMotorClient(config.MONGO_URI)
db = client[config.DATABASE_NAME]

# Collections
users_collection = db.users
profiles_collection = db.profiles
nutrition_targets_collection = db.nutrition_targets
ingredients_collection = db.ingredients
foods_collection = db.foods
food_ingredients_collection = db.food_ingredients
nutrition_comparisons_collection = db.nutrition_comparisons
nutrition_reviews_collection = db.nutrition_reviews
advises_collection = db.advises
daily_reports_collection = db.daily_reports
weekly_reports_collection = db.weekly_reports
weekly_ingredient_usages_collection = db.weekly_ingredient_usages
weekly_report_comments_collection = db.weekly_report_comments
meal_type_standards_collection = db.meal_type_standards
notifications_collection = db.notifications
notification_settings_collection = db.notification_settings

# MongoDB ID helper class
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, _schema_generator, _field_schema):
        return {"type": "string"}

# Database connection dependency
async def get_db():
    try:
        yield db
    finally:
        # Motor manages its own connection pool, no need to close
        pass

# Function to convert MongoDB document to Python dict with string ID
def document_helper(document):
    if document:
        document["id"] = str(document.pop("_id"))
    return document

# Create database indexes to improve query performance
async def create_database_indexes():
    """
    Create indexes on MongoDB collections for better query performance
    """
    try:
        logger.info("Creating database indexes...")
        
        # Users collection indexes
        await users_collection.create_index("email", unique=True)
        await users_collection.create_index("created_at")
        
        # Profiles collection indexes
        await profiles_collection.create_index("user_id", unique=True)
        await profiles_collection.create_index("updated_at")
        
        # Nutrition targets collection indexes
        await nutrition_targets_collection.create_index("user_id", unique=True)
        await nutrition_targets_collection.create_index("updated_at")
        
        # Foods collection indexes
        await foods_collection.create_index("user_id")
        await foods_collection.create_index("date")
        await foods_collection.create_index([("food_name", TEXT)], default_language='english')
        
        # Food ingredients collection indexes
        await food_ingredients_collection.create_index("food_id")
        await food_ingredients_collection.create_index([("name", TEXT)], default_language='english')
        
        # Ingredients collection indexes
        await ingredients_collection.create_index([("name", TEXT)], default_language='english')
        
        # Nutrition comparisons collection indexes
        await nutrition_comparisons_collection.create_index("food_id")
        await nutrition_comparisons_collection.create_index("user_id")
        await nutrition_comparisons_collection.create_index("date")
        
        # Daily reports collection indexes
        await daily_reports_collection.create_index([("user_id", ASCENDING), ("date", ASCENDING)], unique=True)
        await daily_reports_collection.create_index("date")
        
        # Weekly reports collection indexes
        await weekly_reports_collection.create_index([("user_id", ASCENDING), ("week_start_date", ASCENDING)], unique=True)
        await weekly_reports_collection.create_index("week_start_date")
        
        # Weekly ingredient usages collection indexes
        await weekly_ingredient_usages_collection.create_index([("report_id", ASCENDING), ("ingredient_name", ASCENDING)])
        await weekly_ingredient_usages_collection.create_index([("count", DESCENDING)])
        
        # Notifications collection indexes
        await notifications_collection.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        await notifications_collection.create_index([("user_id", ASCENDING), ("is_read", ASCENDING)])
        
        # Notification settings collection indexes
        await notification_settings_collection.create_index("user_id", unique=True)
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating database indexes: {str(e)}")
        raise

# Initialize database function that should be called at application startup
async def initialize_database():
    """
    Initialize database connection and setup
    """
    try:
        # Check database connection
        await db.command("ping")
        logger.info("Successfully connected to MongoDB")
        
        # Create indexes
        await create_database_indexes()
        
        return True
    except Exception as e:
        logger.critical(f"Failed to connect to MongoDB: {str(e)}")
        raise

async def initialize_meal_type_standards():
    """
    Initialize or update the nutritional standards for different meal types
    """
    try:
        # Define default meal type standards
        default_standards = [
            {
                "meal_type": "breakfast",  # Giá trị phải nhất quán với MealTypeEnum.BREAKFAST.value
                "calories_percentage": 25,
                "protein_percentage": 25,
                "fat_percentage": 25,
                "carb_percentage": 30,
                "fiber_percentage": 20,
                "description": "Bữa sáng là bữa ăn quan trọng để cung cấp năng lượng cho cả ngày. Bữa sáng nên giàu protein để tạo cảm giác no lâu và carbohydrate phức hợp để cung cấp năng lượng ổn định."
            },
            {
                "meal_type": "lunch",  # Giá trị phải nhất quán với MealTypeEnum.LUNCH.value
                "calories_percentage": 35,
                "protein_percentage": 30,
                "fat_percentage": 35,
                "carb_percentage": 35,
                "fiber_percentage": 40,
                "description": "Bữa trưa nên cung cấp đủ năng lượng cho các hoạt động buổi chiều. Đây là bữa ăn chính trong ngày, nên cân đối giữa protein, chất béo và carbohydrate."
            },
            {
                "meal_type": "dinner",  # Giá trị phải nhất quán với MealTypeEnum.DINNER.value
                "calories_percentage": 30,
                "protein_percentage": 35,
                "fat_percentage": 30,
                "carb_percentage": 25,
                "fiber_percentage": 30,
                "description": "Bữa tối nên nhẹ nhàng và dễ tiêu hóa, tránh ăn quá nhiều carbohydrate. Nên ưu tiên protein và rau xanh, hạn chế chất béo và đường."
            },
            {
                "meal_type": "snack",  # Giá trị phải nhất quán với MealTypeEnum.SNACK.value
                "calories_percentage": 10,
                "protein_percentage": 10,
                "fat_percentage": 10,
                "carb_percentage": 10,
                "fiber_percentage": 10,
                "description": "Bữa phụ nên nhẹ nhàng và giàu dinh dưỡng, tránh thức ăn nhiều đường và chất béo. Nên chọn trái cây, hạt, sữa chua hoặc protein nhẹ."
            },
            {
                "meal_type": "drinks",  # Giá trị phải nhất quán với MealTypeEnum.DRINKS.value
                "calories_percentage": 5,
                "protein_percentage": 0,
                "fat_percentage": 0,
                "carb_percentage": 0,
                "fiber_percentage": 0,
                "description": "Nên ưu tiên nước lọc, trà xanh không đường, nước ép trái cây tự nhiên. Hạn chế đồ uống có đường và cồn."
            },
            {
                "meal_type": "light_meal",  # Giá trị phải nhất quán với MealTypeEnum.LIGHT_MEAL.value
                "calories_percentage": 15,
                "protein_percentage": 15,
                "fat_percentage": 15,
                "carb_percentage": 15,
                "fiber_percentage": 15,
                "description": "Bữa ăn nhẹ thích hợp cho buổi sáng muộn hoặc chiều tối. Nên cân đối các chất dinh dưỡng, ưu tiên thực phẩm dễ tiêu hóa."
            }
        ]
        
        # For each default standard, either create or update
        for standard in default_standards:
            # Check if standard exists for this meal type
            existing = await meal_type_standards_collection.find_one({"meal_type": standard["meal_type"]})
            
            if existing:
                # Update existing standard
                await meal_type_standards_collection.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {**standard, "updated_at": datetime.utcnow()}}
                )
                logger.info(f"Updated meal type standard for {standard['meal_type']}")
            else:
                # Create new standard
                standard["created_at"] = datetime.utcnow()
                standard["updated_at"] = datetime.utcnow()
                await meal_type_standards_collection.insert_one(standard)
                logger.info(f"Created meal type standard for {standard['meal_type']}")
                
        return True
    except Exception as e:
        logger.error(f"Error initializing meal type standards: {str(e)}")
        raise
