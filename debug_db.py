import asyncio
from src.services.database import db

async def check_rss():
    await db.init()
    async with db.get_connection() as conn:
        cursor = await conn.execute("SELECT key, value FROM preferences")
        rows = await cursor.fetchall()
        print("Current DB Preferences:")
        for row in rows:
            print(f"{row[0]}: {row[1]}")

if __name__ == "__main__":
    asyncio.run(check_rss())
