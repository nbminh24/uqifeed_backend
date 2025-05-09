from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from datetime import date
from typing import Optional
from src.services.export.export_service import export_nutrition_data
from src.services.authentication.user_auth import get_current_user
from io import BytesIO

router = APIRouter(
    prefix="/export",
    tags=["export"]
)

@router.get("/nutrition")
async def export_nutrition_endpoint(
    start_date: date = Query(..., description="Start date for export"),
    end_date: date = Query(..., description="End date for export"),
    format: str = Query("csv", description="Export format (csv, json, excel)"),
    current_user = Depends(get_current_user)
):
    """Export nutrition data"""
    try:
        # Validate format
        if format not in ["csv", "json", "excel"]:
            raise HTTPException(status_code=400, detail="Invalid export format")
            
        # Get export data
        export_data = await export_nutrition_data(
            current_user["id"],
            start_date,
            end_date,
            format
        )
        
        if not export_data:
            raise HTTPException(status_code=400, detail="Failed to export data")
            
        # Create response
        return StreamingResponse(
            BytesIO(export_data["data"].encode() if isinstance(export_data["data"], str) else export_data["data"]),
            media_type=export_data["content_type"],
            headers={
                "Content-Disposition": f"attachment; filename={export_data['filename']}"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 