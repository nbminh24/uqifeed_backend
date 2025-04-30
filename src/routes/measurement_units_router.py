from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from src.config.database import get_db, measurement_units_collection
from src.schemas.schemas import MeasurementUnitCreate, MeasurementUnitResponse, MeasurementUnitUpdate
from src.services.auth_service import get_current_user

router = APIRouter(
    prefix="/settings/measurement-units",
    tags=["settings"],
    dependencies=[Depends(get_current_user)]  # All routes require authentication
)

@router.get("/", response_model=List[MeasurementUnitResponse])
async def get_measurement_units(
    current_user = Depends(get_current_user)
):
    """Get all measurement units for the current user"""
    # Lấy đơn vị đo mặc định của hệ thống
    default_units = await measurement_units_collection.find({
        "is_default": True
    }).to_list(length=100)
    
    # Lấy đơn vị đo tùy chỉnh của người dùng
    user_units = await measurement_units_collection.find({
        "user_id": current_user["id"],
        "is_default": False
    }).to_list(length=100)
    
    # Kết hợp hai danh sách
    units = default_units + user_units
    
    # Add id field for each unit
    for unit in units:
        unit["id"] = str(unit["_id"])
    
    return units

@router.post("/", response_model=MeasurementUnitResponse)
async def create_measurement_unit(
    unit: MeasurementUnitCreate,
    current_user = Depends(get_current_user)
):
    """Create a new custom measurement unit"""
    # Kiểm tra xem đơn vị đo đã tồn tại chưa
    existing_unit = await measurement_units_collection.find_one({
        "name": unit.name,
        "user_id": current_user["id"]
    })
    
    if existing_unit:
        raise HTTPException(status_code=400, detail="Measurement unit with this name already exists")
    
    # Tạo đơn vị đo mới
    new_unit = {
        "name": unit.name,
        "category": unit.category,  # weight, volume, quantity, etc.
        "conversion_factor": unit.conversion_factor,  # Factor to convert to base unit (e.g., grams)
        "base_unit": unit.base_unit,  # Base unit (e.g., "g" for grams)
        "user_id": current_user["id"],
        "is_default": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await measurement_units_collection.insert_one(new_unit)
    created_unit = await measurement_units_collection.find_one({"_id": result.inserted_id})
    
    # Add id field for Pydantic model
    created_unit["id"] = str(created_unit["_id"])
    
    return created_unit

@router.put("/{unit_id}", response_model=MeasurementUnitResponse)
async def update_measurement_unit(
    unit_id: str,
    unit_data: MeasurementUnitUpdate,
    current_user = Depends(get_current_user)
):
    """Update a custom measurement unit"""
    # Kiểm tra xem đơn vị đo tồn tại không
    existing_unit = await measurement_units_collection.find_one({
        "_id": ObjectId(unit_id)
    })
    
    if not existing_unit:
        raise HTTPException(status_code=404, detail="Measurement unit not found")
    
    # Kiểm tra quyền sở hữu
    if existing_unit.get("is_default", False) or existing_unit.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Cannot modify this measurement unit")
    
    # Cập nhật đơn vị đo
    update_data = {k: v for k, v in unit_data.dict(exclude_unset=True).items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()
    
    await measurement_units_collection.update_one(
        {"_id": ObjectId(unit_id)},
        {"$set": update_data}
    )
    
    updated_unit = await measurement_units_collection.find_one({"_id": ObjectId(unit_id)})
    
    # Add id field for Pydantic model
    updated_unit["id"] = str(updated_unit["_id"])
    
    return updated_unit

@router.delete("/{unit_id}")
async def delete_measurement_unit(
    unit_id: str,
    current_user = Depends(get_current_user)
):
    """Delete a custom measurement unit"""
    # Kiểm tra xem đơn vị đo tồn tại không
    existing_unit = await measurement_units_collection.find_one({
        "_id": ObjectId(unit_id)
    })
    
    if not existing_unit:
        raise HTTPException(status_code=404, detail="Measurement unit not found")
    
    # Kiểm tra quyền sở hữu
    if existing_unit.get("is_default", False) or existing_unit.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=403, detail="Cannot delete this measurement unit")
    
    # Xóa đơn vị đo
    await measurement_units_collection.delete_one({"_id": ObjectId(unit_id)})
    
    return {"message": "Measurement unit deleted successfully"}