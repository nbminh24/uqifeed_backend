from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from fastapi import HTTPException
from bson import ObjectId
from pymongo import DESCENDING

from src.config.database import (
    foods_collection, food_ingredients_collection, ingredients_collection,
    nutrition_comparisons_collection, nutrition_targets_collection,
    nutrition_reviews_collection, advises_collection,
    daily_reports_collection, weekly_reports_collection,
    weekly_ingredient_usages_collection, weekly_report_comments_collection,
    meal_type_standards_collection
)

from src.schemas.schemas import (
    FoodCreate, FoodIngredientCreate, IngredientCreate,
    MealTypeNutritionalStandards
)


async def save_food_and_ingredients(
    user_id: str, 
    food_data: Dict[str, Any],
    image_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save food and its ingredients to the database
    
    Args:
        user_id: User ID
        food_data: Food data from recognition
        image_url: URL to the food image
        
    Returns:
        Food object
    """
    try:
        # Create food entry
        food_doc = {
            "user_id": user_id,
            "name": food_data["food_name"],
            "meal_type": food_data.get("meal_type", "lunch"),  # Default value, can be updated
            "total_calories": food_data["total_calories"],
            "total_protein": food_data["total_protein"],
            "total_fat": food_data["total_fat"],
            "total_carb": food_data["total_carb"],
            "total_fiber": food_data["total_fiber"],
            "image_url": image_url,
            "description": f"Automatically detected: {food_data['food_name']}",
            "eating_time": datetime.utcnow(),
            "created_at": datetime.utcnow(),
            "ingredients": []
        }
        
        # Lưu trữ nutrition_review và nutrition_advice nếu có
        if "nutrition_review" in food_data:
            food_doc["nutrition_review"] = food_data["nutrition_review"]
        
        if "nutrition_advice" in food_data:
            food_doc["nutrition_advice"] = food_data["nutrition_advice"]
        
        # Add food to database
        food_result = await foods_collection.insert_one(food_doc)
        food_id = food_result.inserted_id

        # Process ingredients
        for ingredient_data in food_data["ingredients"]:
            # Check if ingredient exists
            db_ingredient = await ingredients_collection.find_one(
                {"name": ingredient_data["name"]}
            )
            
            # If ingredient doesn't exist, create it
            if not db_ingredient:
                ingredient_doc = {
                    "name": ingredient_data["name"],
                    "unit": ingredient_data["unit"],
                    "protein": ingredient_data["protein"],
                    "fat": ingredient_data["fat"],
                    "carb": ingredient_data["carb"],
                    "fiber": ingredient_data["fiber"],
                    "calories": ingredient_data["calories"],
                    "tip": None  # Will be updated later
                }
                ingredient_result = await ingredients_collection.insert_one(ingredient_doc)
                ingredient_id = ingredient_result.inserted_id
            else:
                ingredient_id = db_ingredient["_id"]
            
            # Create food-ingredient relation
            food_ingredient = {
                "food_id": str(food_id),
                "ingredient_id": str(ingredient_id),
                "quantity": ingredient_data["quantity"]
            }
            
            # Add to ingredients list in food document
            await foods_collection.update_one(
                {"_id": food_id},
                {"$push": {"ingredients": food_ingredient}}
            )
        
        # Get the complete food document with ingredients
        food = await foods_collection.find_one({"_id": food_id})
        
        # Convert ObjectId to string
        food["id"] = str(food["_id"])
        
        # Get user's nutrition target
        target = await nutrition_targets_collection.find_one({"user_id": user_id})
        
        # Calculate nutrition score if target exists
        if target:
            # Create a temporary comparison object for score calculation
            comparison = {
                "food_id": food["id"],
                "target_id": str(target["_id"]),
                "meal_type": food_doc["meal_type"]
            }
            
            # Get meal type standards if available
            meal_standard = await get_meal_type_standard(food_doc["meal_type"])
            
            # Apply meal type standards if available
            if meal_standard:
                # Calculate adjusted targets based on meal type percentages
                adjusted_calories = target["target_calories"] * (meal_standard["calories_percentage"] / 100)
                adjusted_protein_grams = (target["target_protein"] / 100) * target["target_calories"] / 4 * (meal_standard["protein_percentage"] / 100)
                adjusted_fat_grams = (target["target_fat"] / 100) * target["target_calories"] / 9 * (meal_standard["fat_percentage"] / 100)
                adjusted_carb_grams = (target["target_carb"] / 100) * target["target_calories"] / 4 * (meal_standard["carb_percentage"] / 100)
                adjusted_fiber = target["target_fiber"] * (meal_standard["fiber_percentage"] / 100)
                
                # Calculate differences using meal-adjusted targets
                comparison["diff_calories"] = food["total_calories"] - adjusted_calories
                comparison["diff_protein"] = food["total_protein"] - adjusted_protein_grams
                comparison["diff_fat"] = food["total_fat"] - adjusted_fat_grams
                comparison["diff_carb"] = food["total_carb"] - adjusted_carb_grams
                comparison["diff_fiber"] = food["total_fiber"] - adjusted_fiber
            else:
                # Calculate differences using standard daily targets
                comparison["diff_calories"] = food["total_calories"] - target["target_calories"]
                
                # For macronutrients, convert percentages to grams for comparison
                target_protein_grams = (target["target_protein"] / 100) * target["target_calories"] / 4
                target_fat_grams = (target["target_fat"] / 100) * target["target_calories"] / 9
                target_carb_grams = (target["target_carb"] / 100) * target["target_calories"] / 4
                
                comparison["diff_protein"] = food["total_protein"] - target_protein_grams
                comparison["diff_fat"] = food["total_fat"] - target_fat_grams
                comparison["diff_carb"] = food["total_carb"] - target_carb_grams
                comparison["diff_fiber"] = food["total_fiber"] - target["target_fiber"]
            
            # Calculate nutrition score
            food["nutrition_score"] = calculate_nutrition_score(comparison)
            
            # Update food record with nutrition score
            await foods_collection.update_one(
                {"_id": food_id},
                {"$set": {"nutrition_score": food["nutrition_score"]}}
            )
        
        return food
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving food: {str(e)}")

async def get_user_foods(
    user_id: str, 
    skip: int = 0, 
    limit: int = 100,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    meal_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get foods created by a user
    
    Args:
        user_id: User ID
        skip: Number of records to skip
        limit: Maximum number of records to return
        start_date: Start date for filtering
        end_date: End date for filtering
        meal_type: Meal type for filtering
        
    Returns:
        List of Food objects
    """
    # Build the query
    query = {"user_id": user_id}
    
    # Apply filters if provided
    if start_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        query["eating_time"] = {"$gte": start_datetime}
    if end_date:
        end_datetime = datetime.combine(end_date, datetime.max.time())
        if "eating_time" in query:
            query["eating_time"]["$lte"] = end_datetime
        else:
            query["eating_time"] = {"$lte": end_datetime}
    if meal_type:
        query["meal_type"] = meal_type
    
    # Execute query with pagination
    foods = await foods_collection.find(query).sort(
        "eating_time", DESCENDING
    ).skip(skip).limit(limit).to_list(length=limit)
    
    # Convert ObjectId to string
    for food in foods:
        food["id"] = str(food["_id"])
    
    return foods

async def get_food_with_ingredients(food_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a food with its ingredients
    
    Args:
        food_id: Food ID
        
    Returns:
        Food object with ingredients loaded
    """
    # Convert string ID to ObjectId if needed
    if isinstance(food_id, str):
        food_id = ObjectId(food_id)
    
    food = await foods_collection.find_one({"_id": food_id})
    
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    
    # Convert ObjectId to string
    food["id"] = str(food["_id"])
    
    return food

async def update_daily_report(user_id: str, report_date: date) -> Dict[str, Any]:
    """
    Update the daily report for a user on a specific date
    
    Args:
        user_id: User ID
        report_date: Date for the report
        
    Returns:
        DailyReport object
    """
    # Convert date to datetime range for query
    start_datetime = datetime.combine(report_date, datetime.min.time())
    end_datetime = datetime.combine(report_date, datetime.max.time())
    
    # Get all foods eaten on the specified date
    foods = await foods_collection.find({
        "user_id": user_id,
        "eating_time": {"$gte": start_datetime, "$lte": end_datetime}
    }).to_list(length=100)
    
    # Calculate totals
    total_calories = sum(food.get("total_calories", 0) for food in foods)
    total_protein = sum(food.get("total_protein", 0) for food in foods)
    total_fat = sum(food.get("total_fat", 0) for food in foods)
    total_carb = sum(food.get("total_carb", 0) for food in foods)
    total_fiber = sum(food.get("total_fiber", 0) for food in foods)
    
    # Calculate average nutrition score
    avg_nutrition_score = 0
    if foods:
        # Get nutrition reviews for foods
        food_ids = [str(food.get("_id")) for food in foods]
        reviews = await nutrition_reviews_collection.find({
            "food_id": {"$in": food_ids}
        }).to_list(length=100)
        
        # Calculate average score if reviews exist
        if reviews:
            avg_nutrition_score = sum(review.get("score", 0) for review in reviews) / len(reviews)
        else:
            avg_nutrition_score = 70  # Default score if no reviews
    
    # Chuyển đổi date thành ISO string format để MongoDB có thể xử lý
    report_date_str = report_date.isoformat()
    
    # Check if report already exists
    report = await daily_reports_collection.find_one({
        "user_id": user_id,
        "report_date": report_date_str
    })
    
    if report:
        # Update existing report
        await daily_reports_collection.update_one(
            {"_id": report["_id"]},
            {"$set": {
                "total_calories": total_calories,
                "total_protein": total_protein,
                "total_fat": total_fat,
                "total_carb": total_carb,
                "total_fiber": total_fiber,
                "avg_nutrition_score": avg_nutrition_score,
                "updated_at": datetime.utcnow()
            }}
        )
    else:
        # Create new report
        report_doc = {
            "user_id": user_id,
            "report_date": report_date_str,
            "total_calories": total_calories,
            "total_protein": total_protein,
            "total_fat": total_fat,
            "total_carb": total_carb,
            "total_fiber": total_fiber,
            "avg_nutrition_score": avg_nutrition_score,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await daily_reports_collection.insert_one(report_doc)
        report = await daily_reports_collection.find_one({"_id": result.inserted_id})
    
    # Convert ObjectId to string
    report["id"] = str(report["_id"])
    
    return report

async def generate_weekly_report(user_id: str, week_start_date: date) -> Dict[str, Any]:
    """
    Generate a weekly report for a user
    
    Args:
        user_id: User ID
        week_start_date: Start date of the week (usually Monday)
        
    Returns:
        WeeklyReport object
    """
    # Calculate week end date (7 days after start date)
    week_end_date = week_start_date + timedelta(days=6)
    
    # Get daily reports for the week
    start_datetime = datetime.combine(week_start_date, datetime.min.time())
    end_datetime = datetime.combine(week_end_date, datetime.max.time())
    
    daily_reports = await daily_reports_collection.find({
        "user_id": user_id,
        "report_date": {"$gte": start_datetime, "$lte": end_datetime}
    }).to_list(length=7)
    
    # If no daily reports, raise exception
    if not daily_reports:
        raise HTTPException(status_code=404, detail="No daily reports found for the specified week")
    
    # Calculate averages
    report_count = len(daily_reports)
    avg_calories = sum(report.get("total_calories", 0) for report in daily_reports) / report_count
    avg_protein = sum(report.get("total_protein", 0) for report in daily_reports) / report_count
    avg_fat = sum(report.get("total_fat", 0) for report in daily_reports) / report_count
    avg_carb = sum(report.get("total_carb", 0) for report in daily_reports) / report_count
    avg_fiber = sum(report.get("total_fiber", 0) for report in daily_reports) / report_count
    
    # Calculate average nutrition score from daily reports
    avg_nutrition_score = sum(report.get("avg_nutrition_score", 70) for report in daily_reports) / report_count
    
    # Check if weekly report already exists
    report = await weekly_reports_collection.find_one({
        "user_id": user_id,
        "week_start_date": week_start_date,
        "week_end_date": week_end_date
    })
    
    if report:
        # Update existing report
        await weekly_reports_collection.update_one(
            {"_id": report["_id"]},
            {"$set": {
                "avg_calories": avg_calories,
                "avg_protein": avg_protein,
                "avg_fat": avg_fat,
                "avg_carb": avg_carb,
                "avg_fiber": avg_fiber,
                "avg_nutrition_score": avg_nutrition_score,
                "updated_at": datetime.utcnow()
            }}
        )
    else:
        # Create new report
        report_doc = {
            "user_id": user_id,
            "week_start_date": week_start_date,
            "week_end_date": week_end_date,
            "avg_calories": avg_calories,
            "avg_protein": avg_protein,
            "avg_fat": avg_fat,
            "avg_carb": avg_carb,
            "avg_fiber": avg_fiber,
            "avg_nutrition_score": avg_nutrition_score,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await weekly_reports_collection.insert_one(report_doc)
        report = await weekly_reports_collection.find_one({"_id": result.inserted_id})
    
    # Convert ObjectId to string
    report["id"] = str(report["_id"])
    
    # Generate ingredient usage statistics
    await generate_weekly_ingredient_usage(report["id"], user_id, week_start_date, week_end_date)
    
    # Generate weekly chart comments
    await generate_weekly_chart_comments(report["id"], {
        "avg_calories": avg_calories,
        "avg_protein": avg_protein,
        "avg_fat": avg_fat,
        "avg_carb": avg_carb,
        "avg_fiber": avg_fiber
    }, user_id)
    
    return report

async def generate_weekly_ingredient_usage(
    weekly_report_id: str,
    user_id: str,
    start_date: date,
    end_date: date
) -> None:
    """
    Generate weekly ingredient usage statistics
    
    Args:
        weekly_report_id: Weekly report ID
        user_id: User ID
        start_date: Start date
        end_date: End date
    """
    # Clear existing usage data for this report
    await weekly_ingredient_usages_collection.delete_many(
        {"weekly_report_id": weekly_report_id}
    )
    
    # Get all foods eaten during the week
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    
    foods = await foods_collection.find({
        "user_id": user_id,
        "eating_time": {"$gte": start_datetime, "$lte": end_datetime}
    }).to_list(length=100)
    
    # Dictionary to track ingredient usage
    ingredient_usage = {}
    
    # Track ingredient usage across all foods
    for food in foods:
        for food_ingredient in food.get("ingredients", []):
            ingredient_id = food_ingredient.get("ingredient_id")
            quantity = food_ingredient.get("quantity", 0)
            
            if ingredient_id in ingredient_usage:
                ingredient_usage[ingredient_id]["count"] += 1
                ingredient_usage[ingredient_id]["total_quantity"] += quantity
            else:
                ingredient_usage[ingredient_id] = {
                    "count": 1,
                    "total_quantity": quantity
                }
    
    # Save usage data to database
    for ingredient_id, usage in ingredient_usage.items():
        usage_doc = {
            "weekly_report_id": weekly_report_id,
            "ingredient_id": ingredient_id,
            "usage_count": usage["count"],
            "total_quantity": usage["total_quantity"],
            "created_at": datetime.utcnow()
        }
        
        await weekly_ingredient_usages_collection.insert_one(usage_doc)

async def generate_weekly_chart_comments(weekly_report_id: str, report_data: Dict[str, Any], user_id: str) -> None:
    """
    Generate comments for each chart type in the weekly report
    
    Args:
        weekly_report_id: Weekly report ID
        report_data: Report data including averages
        user_id: User ID
    """
    # Clear existing comments for this report
    await weekly_report_comments_collection.delete_many(
        {"weekly_report_id": weekly_report_id}
    )
    
    # Get user's nutrition target
    target = await nutrition_targets_collection.find_one({"user_id": user_id})
    if not target:
        # If no target exists, use default values
        target = {
            "target_calories": 2000,
            "target_protein": 30,  # percentage
            "target_fat": 30,      # percentage
            "target_carb": 40,     # percentage
            "target_fiber": 25     # grams
        }
    
    # Calculate target macros in grams
    target_protein_grams = (target["target_protein"] / 100) * target["target_calories"] / 4
    target_fat_grams = (target["target_fat"] / 100) * target["target_calories"] / 9
    target_carb_grams = (target["target_carb"] / 100) * target["target_calories"] / 4
    
    # Calculate actual macros percentages
    total_calories = report_data["avg_calories"]
    if total_calories > 0:
        actual_protein_pct = (report_data["avg_protein"] * 4 / total_calories) * 100
        actual_fat_pct = (report_data["avg_fat"] * 9 / total_calories) * 100
        actual_carb_pct = (report_data["avg_carb"] * 4 / total_calories) * 100
    else:
        actual_protein_pct = 0
        actual_fat_pct = 0
        actual_carb_pct = 0
    
    # Generate comments for each chart type
    comments = []
    
    # Calories chart
    calorie_diff = report_data["avg_calories"] - target["target_calories"]
    calorie_diff_pct = (calorie_diff / target["target_calories"]) * 100 if target["target_calories"] > 0 else 0
    
    if calorie_diff > 300:
        calorie_comment = "High Calorie Diet\nYour calorie intake is significantly above your target. This may lead to weight gain unless balanced with increased physical activity."
        calorie_suggestions = "Consider reducing portion sizes, limiting high-calorie snacks, and focusing on nutrient-dense foods with lower calorie content."
    elif calorie_diff > 100:
        calorie_comment = "Slight Calorie Surplus\nYour calorie intake is slightly above your target. This can be beneficial for muscle gain but monitor your progress."
        calorie_suggestions = "If weight gain isn't your goal, make small adjustments like swapping one high-calorie item for a lower-calorie alternative each day."
    elif calorie_diff < -300:
        calorie_comment = "Low Calorie Diet\nYour calorie intake is significantly below your target. This may lead to nutrient deficiencies and metabolic slowdown if sustained."
        calorie_suggestions = "Increase your intake with nutrient-dense foods like nuts, avocados, olive oil, and whole grains to meet your energy needs."
    elif calorie_diff < -100:
        calorie_comment = "Slight Calorie Deficit\nYour calorie intake is slightly below your target. This can be good for weight loss but ensure you're getting enough nutrients."
        calorie_suggestions = "Focus on high-quality proteins, healthy fats, and complex carbohydrates to maintain energy and muscle mass while in a deficit."
    else:
        calorie_comment = "Balanced Calorie Intake\nYour calorie intake closely matches your target. This is ideal for weight maintenance and overall health."
        calorie_suggestions = "Continue this balanced approach while focusing on food quality and nutrient density for optimal health."
    
    comments.append({
        "weekly_report_id": weekly_report_id,
        "chart_type": "calories",
        "comment": calorie_comment,
        "suggestions": calorie_suggestions
    })
    
    # Protein chart
    protein_diff = report_data["avg_protein"] - target_protein_grams
    protein_diff_pct = (protein_diff / target_protein_grams) * 100 if target_protein_grams > 0 else 0
    
    if protein_diff > 20 or actual_protein_pct > target["target_protein"] + 10:
        protein_comment = "High Protein Diet\nYour protein intake is high. This is ideal for muscle gain or those with specific protein needs. Just ensure it's balanced with some healthy fats and carbs."
        protein_suggestions = "While high protein is beneficial for muscle repair and satiety, too much can strain kidneys over time. Aim for quality sources like lean meats, fish, eggs, dairy, and plant proteins."
    elif protein_diff < -20 or actual_protein_pct < target["target_protein"] - 10:
        protein_comment = "Low Protein Diet\nYour protein intake is lower than recommended. This may impact muscle maintenance, immune function, and satiety."
        protein_suggestions = "Incorporate more protein-rich foods like lean meats, fish, eggs, dairy, legumes, or protein supplements if needed."
    else:
        protein_comment = "Balanced Protein Intake\nYour protein intake is well-aligned with your targets. This supports muscle maintenance, immune function, and proper recovery."
        protein_suggestions = "Continue consuming a variety of protein sources throughout the day to maintain this balanced intake."
    
    comments.append({
        "weekly_report_id": weekly_report_id,
        "chart_type": "protein",
        "comment": protein_comment,
        "suggestions": protein_suggestions
    })
    
    # Fat chart
    fat_diff = report_data["avg_fat"] - target_fat_grams
    fat_diff_pct = (fat_diff / target_fat_grams) * 100 if target_fat_grams > 0 else 0
    
    if fat_diff > 15 or actual_fat_pct > target["target_fat"] + 10:
        fat_comment = "High Fat Diet\nYour fat intake is above your target. While healthy fats are essential, excessive consumption may impact cardiovascular health and weight management."
        fat_suggestions = "Focus on reducing saturated and trans fats while maintaining healthy fats from sources like olive oil, avocados, nuts, and fatty fish."
    elif fat_diff < -15 or actual_fat_pct < target["target_fat"] - 10:
        fat_comment = "Low Fat Diet\nYour fat intake is below recommended levels. Fat is crucial for hormone production, vitamin absorption, and cell health."
        fat_suggestions = "Incorporate more healthy fats like avocados, nuts, seeds, olive oil, and fatty fish to improve vitamin absorption and hormone function."
    else:
        fat_comment = "Balanced Fat Intake\nYour fat intake is well-proportioned with your targets. This supports hormone function, nutrient absorption, and energy levels."
        fat_suggestions = "Maintain this balance while focusing on healthy fat sources such as olive oil, avocados, nuts, seeds, and fatty fish."
    
    comments.append({
        "weekly_report_id": weekly_report_id,
        "chart_type": "fat",
        "comment": fat_comment,
        "suggestions": fat_suggestions
    })
    
    # Carb chart
    carb_diff = report_data["avg_carb"] - target_carb_grams
    carb_diff_pct = (carb_diff / target_carb_grams) * 100 if target_carb_grams > 0 else 0
    
    if carb_diff > 30 or actual_carb_pct > target["target_carb"] + 10:
        carb_comment = "High Carb Diet\nYour carbohydrate intake exceeds your target. While carbs provide essential energy, excess may affect blood sugar and weight management."
        carb_suggestions = "Focus on complex carbohydrates like whole grains, legumes, and vegetables while reducing refined carbs and added sugars."
    elif carb_diff < -30 or actual_carb_pct < target["target_carb"] - 10:
        carb_comment = "Low Carb Diet\nYour carbohydrate intake is below your target. This approach can be beneficial for some but may impact energy levels and exercise performance."
        carb_suggestions = "If experiencing fatigue or decreased performance, consider adding some complex carbs from fruits, starchy vegetables, or whole grains."
    else:
        carb_comment = "Balanced Carb Intake\nYour carbohydrate intake aligns well with your targets. This provides steady energy while supporting overall nutrient balance."
        carb_suggestions = "Continue focusing on complex carbohydrates from whole food sources while minimizing refined carbs and added sugars."
    
    comments.append({
        "weekly_report_id": weekly_report_id,
        "chart_type": "carb",
        "comment": carb_comment,
        "suggestions": carb_suggestions
    })
    
    # Fiber chart
    fiber_diff = report_data["avg_fiber"] - target["target_fiber"]
    fiber_diff_pct = (fiber_diff / target["target_fiber"]) * 100 if target["target_fiber"] > 0 else 0
    
    if fiber_diff > 10:
        fiber_comment = "High Fiber Diet\nYour fiber intake is above recommendations. This supports digestive health, stable blood sugar, and prolonged satiety."
        fiber_suggestions = "Ensure adequate water intake with high fiber consumption to prevent digestive discomfort and aid in proper fiber utilization."
    elif fiber_diff < -5:
        fiber_comment = "Low Fiber Diet\nYour fiber intake is below recommendations. Adequate fiber is crucial for digestive health, disease prevention, and gut microbiome support."
        fiber_suggestions = "Gradually increase fiber by adding more fruits, vegetables, legumes, whole grains, nuts, and seeds to your daily meals."
    else:
        fiber_comment = "Optimal Fiber Intake\nYour fiber intake meets recommendations. This supports gut health, regular digestion, and stable blood sugar levels."
        fiber_suggestions = "Maintain diverse fiber sources from fruits, vegetables, legumes, and whole grains for optimal gut microbiome diversity."
    
    comments.append({
        "weekly_report_id": weekly_report_id,
        "chart_type": "fiber",
        "comment": fiber_comment,
        "suggestions": fiber_suggestions
    })
    
    # Ingredients chart - Chỉ liệt kê nguyên liệu, không đánh giá
    try:
        # Get top used ingredients for the weekly report
        ingredient_usages = await weekly_ingredient_usages_collection.find({
            "weekly_report_id": weekly_report_id
        }).sort("usage_count", -1).limit(10).to_list(length=10)
        
        if ingredient_usages:
            # Get ingredient details
            ingredient_ids = [usage["ingredient_id"] for usage in ingredient_usages]
            ingredients = await ingredients_collection.find({"_id": {"$in": [ObjectId(id) for id in ingredient_ids]}}).to_list(length=len(ingredient_ids))
            
            # Create ingredients map for easy lookup
            ingredients_map = {str(ing["_id"]): ing for ing in ingredients}
            
            ingredient_names = []
            for usage in ingredient_usages:
                ing_id = usage["ingredient_id"]
                if ing_id in ingredients_map:
                    ingredient_names.append(ingredients_map[ing_id]["name"])
            
            if ingredient_names:
                # Chỉ liệt kê nguyên liệu, không thêm đánh giá
                ingredient_list = ", ".join(ingredient_names)
                ingredient_comment = f"Frequently Used Ingredients\n{ingredient_list}"
                ingredient_suggestions = "Click on any ingredient to view its nutritional details."
            else:
                ingredient_comment = "Frequently Used Ingredients\nNo ingredient data available."
                ingredient_suggestions = "Add more meals to see your most used ingredients."
        else:
            ingredient_comment = "Frequently Used Ingredients\nNo ingredient data available."
            ingredient_suggestions = "Add more meals to see your most used ingredients."
    except Exception as e:
        print(f"Error generating ingredient list: {str(e)}")
        ingredient_comment = "Frequently Used Ingredients\nUnable to load ingredient data."
        ingredient_suggestions = "Please try again later."
    
    comments.append({
        "weekly_report_id": weekly_report_id,
        "chart_type": "ingredients",
        "comment": ingredient_comment,
        "suggestions": ingredient_suggestions
    })
    
    # Save all comments to database
    for comment_data in comments:
        await weekly_report_comments_collection.insert_one(comment_data)

async def create_nutrition_comparison(
    food_id: str, 
    user_id: str
) -> Dict[str, Any]:
    """
    Create a nutrition comparison between a food and a user's target
    
    Args:
        food_id: Food ID
        user_id: User ID
        
    Returns:
        NutritionComparison object
    """
    # Import Gemini service
    from src.services.gemini_service import generate_nutrition_comments, generate_advice
    
    # Get the food
    food = await get_food_with_ingredients(food_id)
    
    # Get user's nutrition target
    target = await nutrition_targets_collection.find_one({"user_id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="Nutrition target not found for user")
    
    # Get meal type standards if available
    meal_type = food.get("meal_type", "lunch")
    meal_standard = await get_meal_type_standard(meal_type)
    
    # Apply meal type standards if available
    if meal_standard:
        # Calculate adjusted targets based on meal type percentages
        adjusted_calories = target["target_calories"] * (meal_standard["calories_percentage"] / 100)
        adjusted_protein_grams = (target["target_protein"] / 100) * target["target_calories"] / 4 * (meal_standard["protein_percentage"] / 100)
        adjusted_fat_grams = (target["target_fat"] / 100) * target["target_calories"] / 9 * (meal_standard["fat_percentage"] / 100)
        adjusted_carb_grams = (target["target_carb"] / 100) * target["target_calories"] / 4 * (meal_standard["carb_percentage"] / 100)
        adjusted_fiber = target["target_fiber"] * (meal_standard["fiber_percentage"] / 100)
        
        # Calculate differences using meal-adjusted targets
        diff_calories = food["total_calories"] - adjusted_calories
        diff_protein = food["total_protein"] - adjusted_protein_grams
        diff_fat = food["total_fat"] - adjusted_fat_grams
        diff_carb = food["total_carb"] - adjusted_carb_grams
        diff_fiber = food["total_fiber"] - adjusted_fiber
    else:
        # Calculate differences using standard daily targets
        diff_calories = food["total_calories"] - target["target_calories"]
        
        # For macronutrients, convert percentages to grams for comparison
        target_protein_grams = (target["target_protein"] / 100) * target["target_calories"] / 4  # 4 calories per gram of protein
        target_fat_grams = (target["target_fat"] / 100) * target["target_calories"] / 9  # 9 calories per gram of fat
        target_carb_grams = (target["target_carb"] / 100) * target["target_calories"] / 4  # 4 calories per gram of carb
        
        diff_protein = food["total_protein"] - target_protein_grams
        diff_fat = food["total_fat"] - target_fat_grams
        diff_carb = food["total_carb"] - target_carb_grams
        diff_fiber = food["total_fiber"] - target["target_fiber"]
    
    # Create comparison
    comparison_doc = {
        "food_id": food_id,
        "target_id": str(target["_id"]),
        "diff_calories": diff_calories,
        "diff_protein": diff_protein,
        "diff_fat": diff_fat,
        "diff_carb": diff_carb,
        "diff_fiber": diff_fiber,
        "meal_type": meal_type,
        "compared_at": datetime.utcnow()
    }
    
    # Add reference to meal type standard if available
    if meal_standard:
        comparison_doc["meal_standard_id"] = str(meal_standard["_id"])
    
    result = await nutrition_comparisons_collection.insert_one(comparison_doc)
    comparison = await nutrition_comparisons_collection.find_one({"_id": result.inserted_id})
    
    # Convert ObjectId to string
    comparison["id"] = str(comparison["_id"])
    comparison_id = comparison["id"]
    
    try:
        # Tạo review sử dụng Gemini API
        gemini_comments = await generate_nutrition_comments(comparison)
        
        # Tự động tạo review dựa trên kết quả so sánh
        review_doc = {
            "comparison_id": comparison_id,
            "food_id": food_id,
            "target_id": str(target["_id"]),
            "score": calculate_nutrition_score(comparison),
            "strengths": generate_strengths(comparison),
            "weaknesses": generate_weaknesses(comparison),
            "protein_comment": gemini_comments["protein_comment"],
            "fat_comment": gemini_comments["fat_comment"],
            "carb_comment": gemini_comments["carb_comment"],
            "fiber_comment": gemini_comments["fiber_comment"],
            "calories_comment": gemini_comments["calories_comment"],
            "created_at": datetime.utcnow()
        }
        
        # Tạo advice sử dụng Gemini API
        gemini_advice = await generate_advice(comparison, food)
        
        # Tự động tạo advice dựa trên review
        advice_doc = {
            "comparison_id": comparison_id,
            "food_id": food_id,
            "target_id": str(target["_id"]),
            "recommendations": gemini_advice["recommendations"],
            "substitutions": gemini_advice["substitutions"],
            "tips": gemini_advice["tips"],
            "created_at": datetime.utcnow()
        }
    except Exception as e:
        print(f"Error generating AI-powered comments: {str(e)}")
        # Fallback to standard comment generation
        review_doc = {
            "comparison_id": comparison_id,
            "food_id": food_id,
            "target_id": str(target["_id"]),
            "score": calculate_nutrition_score(comparison),
            "strengths": generate_strengths(comparison),
            "weaknesses": generate_weaknesses(comparison),
            "protein_comment": generate_nutrient_comment(comparison, "diff_protein", "protein"),
            "fat_comment": generate_nutrient_comment(comparison, "diff_fat", "fat"),
            "carb_comment": generate_nutrient_comment(comparison, "diff_carb", "carbohydrate"),
            "fiber_comment": generate_nutrient_comment(comparison, "diff_fiber", "fiber"),
            "calories_comment": generate_nutrient_comment(comparison, "diff_calories", "calorie"),
            "created_at": datetime.utcnow()
        }
        
        # Fallback to standard advice
        advice_doc = {
            "comparison_id": comparison_id,
            "food_id": food_id,
            "target_id": str(target["_id"]),
            "recommendations": generate_recommendations(comparison),
            "substitutions": generate_substitutions(food),
            "tips": generate_tips(comparison),
            "created_at": datetime.utcnow()
        }
    
    await nutrition_reviews_collection.insert_one(review_doc)
    await advises_collection.insert_one(advice_doc)
    
    return comparison
    
# Hàm hỗ trợ để tính điểm dinh dưỡng
def calculate_nutrition_score(comparison: Dict[str, Any]) -> int:
    """Calculate a nutrition score based on how well the food matches the target"""
    # Base score is 70 out of 100
    score = 70
    
    # Add or subtract points based on the differences
    # Calories: max ±10 points
    calories_diff_percent = abs(comparison.get("diff_calories", 0)) / 500 * 100
    if calories_diff_percent <= 10:
        # Less than 10% difference is good
        score += 5
    elif calories_diff_percent >= 30:
        # More than 30% difference is bad
        score -= 10
    
    # Protein: max ±10 points
    protein_diff_percent = abs(comparison.get("diff_protein", 0)) / 30 * 100
    if protein_diff_percent <= 10:
        score += 5
    elif protein_diff_percent >= 30:
        score -= 5
    
    # Other nutrients: max ±5 points each
    for nutrient, limit in [("diff_fat", 20), ("diff_carb", 50), ("diff_fiber", 10)]:
        diff_percent = abs(comparison.get(nutrient, 0)) / limit * 100
        if diff_percent <= 10:
            score += 3
        elif diff_percent >= 30:
            score -= 3
    
    # Ensure score is between 0 and 100
    return max(0, min(100, score))

def generate_strengths(comparison: Dict[str, Any]) -> List[str]:
    """Generate list of nutritional strengths based on comparison"""
    strengths = []
    
    # Check for positive aspects
    if abs(comparison.get("diff_calories", 0)) < 100:
        strengths.append("Calories close to target")
    
    if comparison.get("diff_protein", 0) >= 0:
        strengths.append("Good protein content")
    
    if comparison.get("diff_fiber", 0) >= 0:
        strengths.append("Good fiber content")
    
    # Add generic strength if none found
    if not strengths:
        strengths.append("Balanced nutritional profile")
    
    return strengths

def generate_weaknesses(comparison: Dict[str, Any]) -> List[str]:
    """Generate list of nutritional weaknesses based on comparison"""
    weaknesses = []
    
    # Check for negative aspects
    if comparison.get("diff_calories", 0) > 200:
        weaknesses.append("Higher calories than target")
    
    if comparison.get("diff_protein", 0) < -10:
        weaknesses.append("Lower protein than recommended")
    
    if comparison.get("diff_fat", 0) > 10:
        weaknesses.append("Higher fat content than target")
    
    if comparison.get("diff_carb", 0) > 20:
        weaknesses.append("Higher carbohydrate content than target")
    
    # Add generic weakness if none found
    if not weaknesses:
        weaknesses.append("Minor deviations from nutritional targets")
    
    return weaknesses

def generate_recommendations(comparison: Dict[str, Any]) -> List[str]:
    """Generate recommendations based on comparison"""
    recommendations = []
    
    # Calorie recommendations
    if comparison.get("diff_calories", 0) > 200:
        recommendations.append("Giảm khẩu phần ăn khoảng 20-30% để cân bằng lượng calories. Bạn cũng có thể tăng cường hoạt động thể chất như đi bộ thêm 30 phút để đốt calories dư thừa.")
    elif comparison.get("diff_calories", 0) < -200:
        recommendations.append("Tăng khẩu phần ăn hoặc thêm thực phẩm giàu năng lượng như bơ đậu phộng, các loại hạt, hoặc dầu olive vào bữa ăn.")
    
    # Protein recommendations
    if comparison.get("diff_protein", 0) < -10:
        recommendations.append("Bổ sung thêm nguồn protein như thịt gà (25-30g protein/100g), thịt bò nạc (26g protein/100g), cá hồi (20g protein/100g) hoặc đậu hũ (8g protein/100g) nếu bạn ăn chay.")
    elif comparison.get("diff_protein", 0) > 20:
        recommendations.append("Lượng protein cao hơn mục tiêu đáng kể. Cân nhắc giảm các thực phẩm giàu protein và đảm bảo uống đủ nước để hỗ trợ thận lọc protein dư thừa.")
    
    # Fat recommendations
    if comparison.get("diff_fat", 0) > 10:
        recommendations.append("Giảm chất béo bằng cách hạn chế thực phẩm chiên rán, chọn phương pháp nấu ăn như hấp, luộc hoặc nướng. Thay thế sữa nguyên kem bằng sữa ít béo.")
    elif comparison.get("diff_fat", 0) < -10:
        recommendations.append("Tăng cường chất béo lành mạnh từ các nguồn như cá béo (cá hồi, cá thu), bơ, dầu olive, các loại hạt (óc chó, hạnh nhân) và hạt chia.")
    
    # Carb recommendations
    if comparison.get("diff_carb", 0) > 20:
        recommendations.append("Giảm carbohydrate bằng cách giảm khẩu phần cơm, bánh mì, mì và thay thế một phần bằng rau xanh. Chọn carbs phức hợp như gạo lứt thay vì gạo trắng.")
    elif comparison.get("diff_carb", 0) < -20:
        recommendations.append("Tăng carbohydrate phức hợp như khoai lang (20g carb/100g), gạo lứt (23g carb/100g), yến mạch (12g carb/40g), hoặc quinoa (21g carb/100g).")
    
    # Fiber recommendations
    if comparison.get("diff_fiber", 0) < -5:
        recommendations.append("Bổ sung chất xơ bằng các loại rau như bông cải xanh (2.6g/100g), đậu lăng (7.9g/100g), táo (4.4g/quả) hoặc yến mạch (10.6g/100g). Thêm hạt chia (10g chất xơ/28g) vào sinh tố cũng rất hiệu quả.")
    
    # Add generic recommendation if none found
    if not recommendations:
        recommendations.append("Chế độ ăn của bạn khá cân đối với mục tiêu dinh dưỡng. Tiếp tục duy trì và đa dạng hóa nguồn thực phẩm để đảm bảo đủ vi chất.")
    
    return recommendations

def generate_substitutions(food: Dict[str, Any]) -> List[Dict[str, str]]:
    """Generate substitution recommendations for food ingredients"""
    substitutions = []
    
    # Sample substitutions based on common ingredients
    ingredients = food.get("ingredients", [])
    for ingredient in ingredients:
        name = ingredient.get("name", "").lower() if isinstance(ingredient, dict) else ""
        
        if "rice" in name or "cơm" in name:
            substitutions.append({
                "original": "Cơm trắng",
                "substitute": "Cơm gạo lứt hoặc gạo đỏ",
                "benefit": "Tăng chất xơ (3.5g/100g gạo lứt so với 0.4g/100g gạo trắng) và giảm tác động đường huyết"
            })
        elif "pasta" in name or "mì" in name or "bún" in name:
            substitutions.append({
                "original": "Mì trắng, bún thường",
                "substitute": "Mì nguyên cám, bún gạo lứt, mì rau củ (mì bí đỏ, mì rau chân vịt)",
                "benefit": "Tăng chất xơ (5-7g/100g) và vitamin, khoáng chất"
            })
        elif "beef" in name or "thịt bò" in name:
            substitutions.append({
                "original": "Thịt bò thường",
                "substitute": "Thịt bò nạc, ức gà, cá hồi hoặc đậu lăng",
                "benefit": "Giảm chất béo bão hòa (từ 15g xuống 4-7g/100g), tăng protein chất lượng cao (22-25g/100g)"
            })
        elif "pork" in name or "thịt heo" in name or "thịt lợn" in name:
            substitutions.append({
                "original": "Thịt heo thường",
                "substitute": "Thịt heo nạc, thịt gà không da, cá biển, đậu hũ",
                "benefit": "Giảm chất béo (từ 14-22g xuống 4-8g/100g) mà vẫn đảm bảo protein (20-25g/100g)"
            })
        elif "oil" in name or "dầu" in name:
            substitutions.append({
                "original": "Dầu thực vật thông thường",
                "substitute": "Dầu olive, dầu hạt lanh, nước hầm xương, nước luộc rau",
                "benefit": "Tăng chất béo lành mạnh omega-3, giảm calories (120 kcal/tbsp dầu olive thay vì 250 kcal/tbsp khi chiên ngập dầu)"
            })
        elif "bread" in name or "bánh mì" in name:
            substitutions.append({
                "original": "Bánh mì trắng",
                "substitute": "Bánh mì nguyên cám, bánh mì đa ngũ cốc, bánh mì hạt",
                "benefit": "Tăng chất xơ (5-8g/100g) và protein (8-10g/100g), giảm chỉ số đường huyết"
            })
        elif "milk" in name or "sữa" in name:
            substitutions.append({
                "original": "Sữa nguyên kem",
                "substitute": "Sữa ít béo, sữa hạnh nhân không đường, sữa yến mạch",
                "benefit": "Giảm chất béo bão hòa và calories (từ 150 kcal xuống 30-80 kcal/cốc)"
            })
        elif "sugar" in name or "đường" in name:
            substitutions.append({
                "original": "Đường trắng",
                "substitute": "Mật ong, đường dừa, lá stevia, trái cây xay nhuyễn",
                "benefit": "Hàm lượng khoáng chất cao hơn, chỉ số đường huyết thấp hơn, ít calories hơn"
            })
    
    # Add general substitutions based on food type
    food_name = food.get("name", "").lower()
    
    if "salad" in food_name or "rau" in food_name:
        substitutions.append({
            "original": "Nước sốt salad thông thường",
            "substitute": "Dầu olive + chanh/giấm táo, sốt sữa chua Hy Lạp ít béo",
            "benefit": "Giảm calories và chất béo (50 kcal/tbsp thay vì 120 kcal/tbsp)"
        })
    elif "soup" in food_name or "canh" in food_name:
        substitutions.append({
            "original": "Nước dùng xương thường",
            "substitute": "Nước dùng rau củ, nước dùng xương hầm không mỡ",
            "benefit": "Giảm chất béo bão hòa và natri, tăng vitamin"
        })
    elif "dessert" in food_name or "bánh ngọt" in food_name or "tráng miệng" in food_name:
        substitutions.append({
            "original": "Bánh ngọt thông thường",
            "substitute": "Trái cây tươi, sữa chua Hy Lạp với mật ong, bánh làm từ bột yến mạch",
            "benefit": "Tăng protein (8-10g/100g), giảm đường tinh chế và calories (giảm 100-200 kcal/phần)"
        })
    
    # Add generic substitution if none found
    if not substitutions:
        substitutions.append({
            "original": "Thực phẩm chế biến sẵn",
            "substitute": "Thực phẩm tự chế biến từ nguyên liệu tươi sống",
            "benefit": "Kiểm soát tốt hơn lượng muối, đường, chất béo và phụ gia"
        })
    
    return substitutions

def generate_tips(comparison: Dict[str, Any]) -> List[str]:
    """Generate general nutrition tips based on comparison"""
    all_tips = [
        "Uống 2-3 lít nước mỗi ngày để tăng cường trao đổi chất, nhất là trước bữa ăn để giảm cảm giác thèm ăn và hỗ trợ tiêu hóa.",
        "Áp dụng nguyên tắc 'đĩa ăn cân bằng': 1/2 đĩa là rau củ, 1/4 đĩa là protein, 1/4 đĩa là tinh bột phức hợp.",
        "Chuẩn bị các bữa ăn và bữa phụ lành mạnh từ trước để tránh ăn vặt không lành mạnh khi đói.",
        "Chọn các phương pháp chế biến lành mạnh như hấp, luộc, nướng thay vì chiên rán, đồng thời giảm lượng muối và đường trong nấu ăn.",
        "Bổ sung các thực phẩm lên men như kim chi, sữa chua để cải thiện hệ vi sinh đường ruột.",
        "Ăn chậm và nhai kỹ, dành ít nhất 20 phút cho mỗi bữa ăn để cơ thể có thời gian nhận tín hiệu no.",
        "Ưu tiên thực phẩm tươi sống, tránh thực phẩm chế biến sẵn, đồ ăn nhanh và đồ uống có đường.",
        "Điều chỉnh thời gian ăn phù hợp với lịch tập luyện: protein và carbs phức hợp trước khi tập, protein và carbs đơn giản sau khi tập.",
        "Đảm bảo dung nạp đủ protein khoảng 1.2-2g/kg cân nặng mỗi ngày để duy trì và phát triển cơ bắp.",
        "Kiểm soát khẩu phần ăn bằng cách sử dụng đĩa nhỏ hơn và chú ý đến kích thước khẩu phần."
    ]
    
    specific_tips = []
    
    # Đưa ra lời khuyên dựa trên sự chênh lệch protein
    if comparison.get("diff_protein", 0) < -10:
        specific_tips.append("Phân chia đều lượng protein qua các bữa ăn trong ngày, mỗi bữa 20-30g protein để tối ưu hóa hấp thu và tổng hợp protein cơ bắp.")
        
    # Đưa ra lời khuyên về chất béo
    if comparison.get("diff_fat", 0) > 15:
        specific_tips.append("Đảm bảo tỷ lệ omega-3:omega-6 cân bằng bằng cách ưu tiên các loại cá béo, hạt lanh và giảm dầu thực vật tinh chế.")
        
    # Đưa ra lời khuyên về carb và chất xơ
    if comparison.get("diff_carb", 0) > 20 or comparison.get("diff_fiber", 0) < -5:
        specific_tips.append("Ưu tiên carbohydrate có chỉ số đường huyết thấp như yến mạch, gạo lứt, và đa dạng rau xanh để ổn định năng lượng suốt ngày.")
    
    # Kết hợp lời khuyên cụ thể và lời khuyên chung
    combined_tips = specific_tips + all_tips
    
    # Trả về 3 lời khuyên đầu tiên
    return combined_tips[:3]

# Hàm để tạo comment cho từng loại dinh dưỡng
def generate_nutrient_comment(comparison: Dict[str, Any], diff_key: str, nutrient_name: str) -> str:
    """Generate comment for a specific nutrient based on comparison"""
    diff_value = comparison.get(diff_key, 0)
    
    # Protein comments
    if nutrient_name == "protein":
        if diff_value <= -20:  # Quá ít
            return "Protein's missing! Try adding lean meat, tofu, or legumes — too little can lead to fatigue and muscle loss."
        elif diff_value < 0:  # Thiếu nhẹ
            return "A bit more protein from eggs, yogurt, or beans could help maintain strength and fullness."
        elif diff_value <= 15:  # Đạt chuẩn
            return "Nice! Your protein intake is well-balanced for daily needs."
        else:  # Thừa nhiều
            return "High on protein — great for muscle support, but long-term excess may strain your kidneys."
    
    # Fat comments
    elif nutrient_name == "fat":
        if diff_value <= -20:  # Quá ít
            return "Very low fat — try adding avocado or olive oil to improve vitamin absorption and hormone balance."
        elif diff_value < 0:  # Thiếu nhẹ
            return "A small dose of healthy fats can round out your meal and support overall wellness."
        elif diff_value <= 10:  # Đạt chuẩn
            return "Well done! Your fat intake supports energy without overdoing it."
        else:  # Thừa nhiều
            return "This meal is quite rich — high fat, especially if saturated, can raise cholesterol over time."
    
    # Carbohydrate comments
    elif nutrient_name == "carbohydrate":
        if diff_value <= -20:  # Quá ít
            return "Low-carb detected — consider pairing with grains or fruit to avoid fatigue and brain fog."
        elif diff_value < 0:  # Thiếu nhẹ
            return "A small boost of complex carbs could help sustain energy levels longer."
        elif diff_value <= 20:  # Đạt chuẩn
            return "Carb intake is on point — a solid source of energy without overload."
        else:  # Thừa nhiều
            return "Carbs are a bit high — cutting back on starch or sugar can prevent energy crashes and weight gain."
    
    # Fiber comments
    elif nutrient_name == "fiber":
        if diff_value <= -10:  # Quá ít
            return "Very low in fiber — try adding vegetables or whole grains to support digestion and prevent constipation."
        elif diff_value < 0:  # Thiếu nhẹ
            return "A bit more fiber from salad or beans can improve satiety and gut health."
        elif diff_value <= 5:  # Đạt chuẩn
            return "Nice! Your fiber intake supports healthy digestion and fullness."
        else:  # Thừa nhiều
            return "This is high in fiber — great for fullness, but drink enough water to avoid bloating."
    
    # Calorie comments (giữ nguyên logic cũ cho calories)
    else:
        if abs(diff_value) < 100:
            return f"Your calorie intake is well balanced with your target."
        elif diff_value > 200:
            return f"Your calorie intake is significantly higher than your target."
        elif diff_value > 100:
            return f"Your calorie intake is moderately higher than your target."
        elif diff_value < -200:
            return f"Your calorie intake is significantly lower than your target."
        elif diff_value < -100:
            return f"Your calorie intake is moderately lower than your target."
        else:
            return f"Your calorie intake is slightly off from your target."

async def get_meal_type_standard(meal_type: str):
    """
    Get nutritional standards for a specific meal type
    
    Args:
        meal_type: Meal type (breakfast, lunch, dinner, snack, drinks, light_meal)
        
    Returns:
        Meal type standard object or None if not found
    """
    standard = await meal_type_standards_collection.find_one({"meal_type": meal_type})
    if standard:
        standard["id"] = str(standard["_id"])
    
    return standard
