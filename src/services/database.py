import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


async def get_db():
    """Kết nối đến database PostgreSQL"""
    try:
        print(f"Kết nối đến database với URL: {DATABASE_URL}")
        conn = await asyncpg.connect(DATABASE_URL)
        print("Kết nối database thành công!")
        return conn
    except Exception as e:
        print(f"Lỗi khi kết nối database: {e}")
        return None
