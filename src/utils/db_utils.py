from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException
import asyncio
import logging
from datetime import datetime
import structlog

# Configure structured logging
logger = structlog.get_logger()

# Configure MongoDB client with connection pooling
client = AsyncIOMotorClient(
    "mongodb://localhost:27017",
    maxPoolSize=50,
    minPoolSize=10,
    maxIdleTimeMS=30000,
    waitQueueTimeoutMS=10000,
    retryWrites=True,
    retryReads=True
)

# Database collections
db = client.uqifeed
profiles_collection = db.profiles
nutrition_targets_collection = db.nutrition_targets

async def safe_db_operation(operation, timeout=5, max_retries=3):
    """Execute database operation with timeout and retry handling"""
    for attempt in range(max_retries):
        try:
            start_time = datetime.now()
            result = await asyncio.wait_for(operation, timeout=timeout)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Log successful operation with metrics
            logger.info(
                "db_operation_success",
                attempt=attempt + 1,
                execution_time=execution_time,
                operation_type=operation.__name__ if hasattr(operation, '__name__') else 'unknown'
            )
            return result
            
        except asyncio.TimeoutError:
            if attempt == max_retries - 1:
                logger.error(
                    "db_operation_timeout",
                    attempt=attempt + 1,
                    max_retries=max_retries
                )
                raise HTTPException(
                    status_code=503,
                    detail="Database operation timed out"
                )
            await asyncio.sleep(1)  # Wait before retry
            
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(
                    "db_operation_failed",
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=max_retries
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Database operation failed: {str(e)}"
                )
            await asyncio.sleep(1)

async def get_db_stats():
    """Get database connection pool statistics"""
    try:
        stats = await db.command("serverStatus")
        return {
            "connections": stats.get("connections", {}),
            "opcounters": stats.get("opcounters", {}),
            "mem": stats.get("mem", {}),
            "uptime": stats.get("uptime", 0)
        }
    except Exception as e:
        logger.error("failed_to_get_db_stats", error=str(e))
        return None

async def create_indexes():
    """Create necessary database indexes"""
    try:
        # Profile indexes
        await profiles_collection.create_index("user_id", unique=True)
        await profiles_collection.create_index("email", unique=True)
        await profiles_collection.create_index("created_at")
        await profiles_collection.create_index("updated_at")
        
        # Nutrition targets indexes
        await nutrition_targets_collection.create_index("user_id", unique=True)
        await nutrition_targets_collection.create_index("created_at")
        
        # Compound indexes for common queries
        await profiles_collection.create_index([
            ("user_id", 1),
            ("profile_completed", 1)
        ])
        
        await nutrition_targets_collection.create_index([
            ("user_id", 1),
            ("created_at", -1)
        ])
        
        logger.info("database_indexes_created")
    except Exception as e:
        logger.error("failed_to_create_indexes", error=str(e))
        raise 