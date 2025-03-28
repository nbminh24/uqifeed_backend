import asyncio
from database import get_db

async def test_connection():
    """Kiểm tra kết nối đến database"""
    try:
        db = await get_db()
        print("Kết nối database thành công!")
        await db.close()
    except Exception as e:
        print(f"Lỗi kết nối database: {e}")

async def test_query():
    """Thực hiện một truy vấn đơn giản để kiểm tra"""
    try:
        db = await get_db()
        print("Kết nối database thành công!")

        # Thực hiện truy vấn kiểm tra
        result = await db.fetch("SELECT 1 AS test;")
        print("Kết quả truy vấn:", result)

        await db.close()
    except Exception as e:
        print(f"Lỗi khi thực hiện truy vấn: {e}")

if __name__ == "__main__":
    # Chạy kiểm tra kết nối
    print("Đang kiểm tra kết nối database...")
    asyncio.run(test_connection())

    # Chạy kiểm tra truy vấn
    print("Đang kiểm tra truy vấn database...")
    asyncio.run(test_query())