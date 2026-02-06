import aiosqlite
from src.config import settings
from src.services.logger import logger
import json
from datetime import datetime

INIT_SQL = """
CREATE TABLE IF NOT EXISTS items (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT,
    url TEXT,
    content TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluations (
    item_id TEXT PRIMARY KEY,
    persona TEXT NOT NULL,
    score FLOAT,
    decision TEXT,
    reasoning TEXT,
    evaluation_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(item_id) REFERENCES items(id)
);

CREATE TABLE IF NOT EXISTS digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE,
    persona TEXT,
    content_json JSON,
    content_markdown TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

class Database:
    def __init__(self):
        self.db_path = settings.DATA_DIR / "intelligence.db"

    async def init(self):
        settings.ensure_dirs()
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(INIT_SQL)
            await db.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def get_connection(self):
        return aiosqlite.connect(self.db_path)

    async def save_item(self, item) -> bool:
        """Saves an IngestedItem to the DB."""
        async with self.get_connection() as conn:
            try:
                await conn.execute(
                    """
                    INSERT OR IGNORE INTO items (id, source, title, url, content, metadata, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (item.id, item.source, item.title, item.url, item.content, json.dumps(item.metadata), item.created_at)
                )
                await conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to save item {item.id}: {e}")
                return False

    async def get_recent_items(self, limit: int = 100):
        """Fetches recent items for RAG generation."""
        async with self.get_connection() as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT * FROM items ORDER BY created_at DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
            return rows

    async def get_preference(self, key: str, default: str = "true") -> str:
        """Fetch a preference value from DB."""
        async with self.get_connection() as conn:
            cursor = await conn.execute("SELECT value FROM preferences WHERE key = ?", (key,))
            row = await cursor.fetchone()
            return row[0] if row else default

db = Database()
