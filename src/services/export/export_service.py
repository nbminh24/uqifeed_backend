from typing import Dict, Any, List
from datetime import datetime, date, timedelta
import csv
import json
import pandas as pd
from io import StringIO
import logging
from src.services.calorie.calorie_service import get_weekly_statistics
from src.services.user.profile_manager import get_user_profile
from src.utils.db_utils import safe_db_operation
from src.config.database import nutrition_logs_collection
from fastapi import HTTPException

logger = logging.getLogger(__name__)

MAX_EXPORT_DAYS = 365
VALID_EXPORT_FORMATS = ["csv", "json", "excel"]

async def export_nutrition_data(
    user_id: str,
    start_date: date,
    end_date: date,
    format: str = "csv"
) -> Dict[str, Any]:
    """
    Export nutrition data with validation
    """
    try:
        # Validate date range
        if end_date < start_date:
            raise HTTPException(
                status_code=400,
                detail="End date must be after start date"
            )
            
        date_range = (end_date - start_date).days
        if date_range > MAX_EXPORT_DAYS:
            raise HTTPException(
                status_code=400,
                detail=f"Export range cannot exceed {MAX_EXPORT_DAYS} days"
            )
            
        # Validate format
        if format not in VALID_EXPORT_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid export format. Must be one of: {VALID_EXPORT_FORMATS}"
            )
            
        # Get user profile
        user = await get_user_profile(user_id)
        if not user:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )
            
        # Get nutrition logs
        logs = await safe_db_operation(
            nutrition_logs_collection.find(
                {
                    "user_id": user_id,
                    "date": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                }
            ).sort("date", 1)
        )
        
        # Convert to list
        logs_list = list(logs)
        
        if not logs_list:
            raise HTTPException(
                status_code=404,
                detail="No nutrition data found for the specified date range"
            )
        
        # Format data based on export type
        if format == "csv":
            return await export_to_csv(logs_list, user)
        elif format == "json":
            return await export_to_json(logs_list, user)
        elif format == "excel":
            return await export_to_excel(logs_list, user)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting nutrition data: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

async def export_to_csv(logs: List[Dict], user: Dict) -> Dict[str, Any]:
    """Export data to CSV format with error handling"""
    try:
        # Create CSV string
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "date", "meal_type", "food_name", "calories",
            "protein", "carbs", "fat", "fiber"
        ])
        
        writer.writeheader()
        
        for log in logs:
            for meal in log.get("meals", []):
                writer.writerow({
                    "date": log["date"].strftime("%Y-%m-%d"),
                    "meal_type": meal.get("type", ""),
                    "food_name": meal.get("name", ""),
                    "calories": meal.get("total_calories", 0),
                    "protein": meal.get("total_protein", 0),
                    "carbs": meal.get("total_carbs", 0),
                    "fat": meal.get("total_fat", 0),
                    "fiber": meal.get("total_fiber", 0)
                })
                
        return {
            "data": output.getvalue(),
            "filename": f"nutrition_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "content_type": "text/csv"
        }
        
    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export data to CSV"
        )

async def export_to_json(logs: List[Dict], user: Dict) -> Dict[str, Any]:
    """Export data to JSON format with error handling"""
    try:
        # Format data
        export_data = {
            "user": {
                "name": user.get("name", ""),
                "email": user.get("email", "")
            },
            "export_date": datetime.now().isoformat(),
            "logs": logs
        }
        
        return {
            "data": json.dumps(export_data, default=str),
            "filename": f"nutrition_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "content_type": "application/json"
        }
        
    except Exception as e:
        logger.error(f"Error exporting to JSON: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export data to JSON"
        )

async def export_to_excel(logs: List[Dict], user: Dict) -> Dict[str, Any]:
    """Export data to Excel format with error handling"""
    try:
        # Convert to DataFrame
        data = []
        for log in logs:
            for meal in log.get("meals", []):
                data.append({
                    "date": log["date"],
                    "meal_type": meal.get("type", ""),
                    "food_name": meal.get("name", ""),
                    "calories": meal.get("total_calories", 0),
                    "protein": meal.get("total_protein", 0),
                    "carbs": meal.get("total_carbs", 0),
                    "fat": meal.get("total_fat", 0),
                    "fiber": meal.get("total_fiber", 0)
                })
                
        df = pd.DataFrame(data)
        
        # Create Excel file
        output = StringIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Nutrition Data', index=False)
            
            # Add summary sheet
            summary_df = df.groupby('date').agg({
                'calories': 'sum',
                'protein': 'sum',
                'carbs': 'sum',
                'fat': 'sum',
                'fiber': 'sum'
            }).reset_index()
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
        return {
            "data": output.getvalue(),
            "filename": f"nutrition_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
        
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export data to Excel"
        ) 