import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
import logging

# Import services
from src.services.database import db
from src.workflows.pipeline import pipeline
from src.config import settings
from src.services.logger import logger

# Telegram Bot
_telegram_bot_app = None
_telegram_bot_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _telegram_bot_app, _telegram_bot_task
    
    await db.init()
    
    # Start Telegram Bot if configured
    if settings.TELEGRAM_ENABLED and settings.TELEGRAM_BOT_TOKEN:
        try:
            from src.services.telegram_bot import create_telegram_bot
            _telegram_bot_app = create_telegram_bot()
            if _telegram_bot_app:
                await _telegram_bot_app.initialize()
                await _telegram_bot_app.start()
                await _telegram_bot_app.updater.start_polling()
                logger.info("🤖 Telegram Bot started and listening for commands!")
        except Exception as e:
            logger.error(f"Failed to start Telegram Bot: {e}")
    
    yield
    
    # Cleanup on shutdown
    if _telegram_bot_app:
        logger.info("Stopping Telegram Bot...")
        await _telegram_bot_app.updater.stop()
        await _telegram_bot_app.stop()
        await _telegram_bot_app.shutdown()

app = FastAPI(title="AI Intelligence Digest API", lifespan=lifespan)

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Preference(BaseModel):
    key: str
    value: str

class RunRequest(BaseModel):
    force: bool = False
    summary_mode: bool = False

@app.get("/api/status")
async def get_status():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/api/preferences")
async def get_preferences():
    # Return all preferences with DB overrides
    async with db.get_connection() as conn:
        async with conn.execute("SELECT key, value FROM preferences") as cursor:
            rows = await cursor.fetchall()
            db_prefs = {row[0]: row[1] for row in rows}
            
    return {
        # Personas
        "PERSONA_GENAI_NEWS_ENABLED": db_prefs.get("PERSONA_GENAI_NEWS_ENABLED", "true"),
        "PERSONA_PRODUCT_IDEAS_ENABLED": db_prefs.get("PERSONA_PRODUCT_IDEAS_ENABLED", "true"),
        "PERSONA_FINANCE_ENABLED": db_prefs.get("PERSONA_FINANCE_ENABLED", "true"),
        # Sources
        "SOURCE_HN_ENABLED": db_prefs.get("SOURCE_HN_ENABLED", "true"),
        "SOURCE_REDDIT_ENABLED": db_prefs.get("SOURCE_REDDIT_ENABLED", "true"),
        "SOURCE_RSS_ENABLED": db_prefs.get("SOURCE_RSS_ENABLED", "true"),
        # Delivery
        "DELIVERY_EMAIL_ENABLED": db_prefs.get("DELIVERY_EMAIL_ENABLED", "true"),
        "DELIVERY_TELEGRAM_ENABLED": db_prefs.get("DELIVERY_TELEGRAM_ENABLED", "true"),
    }

@app.post("/api/preferences")
async def update_preferences(prefs: List[Preference]):
    async with db.get_connection() as conn:
        for p in prefs:
            await conn.execute(
                "INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)",
                (p.key, str(p.value).lower())
            )
        await conn.commit()
    return {"status": "updated"}

@app.get("/api/digests")
async def list_digests():
    # List files in data dir or reading from DB
    import os
    files = []
    # Simple file listing for MVP
    try:
        files = [f for f in os.listdir(settings.DATA_DIR) if f.startswith("digest_") and f.endswith(".md")]
        files.sort(reverse=True)
    except Exception:
        pass
    return {"digests": files}

@app.get("/api/digests/{filename}")
async def get_digest(filename: str):
    import os
    path = settings.DATA_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Digest not found")
    
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"filename": filename, "content": content}

async def run_pipeline_task(summary_mode: bool = False):
    # Need to patch settings with DB values before running
    # This acts as a 'middleware' for the pipeline configuration
    try:
        async with db.get_connection() as conn:
             async with conn.execute("SELECT key, value FROM preferences") as cursor:
                rows = await cursor.fetchall()
                for key, val in rows:
                    if key == "PERSONA_GENAI_NEWS_ENABLED":
                        settings.PERSONA_GENAI_NEWS_ENABLED = (val == "true")
                    elif key == "PERSONA_PRODUCT_IDEAS_ENABLED":
                        settings.PERSONA_PRODUCT_IDEAS_ENABLED = (val == "true")
                    elif key == "PERSONA_FINANCE_ENABLED":
                        settings.PERSONA_FINANCE_ENABLED = (val == "true")
        
        await pipeline.run_pipeline(summary_mode=summary_mode)
    except Exception as e:
        logger.error(f"Pipeline run failed: {e}")

@app.post("/api/run")
async def trigger_run(req: RunRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(run_pipeline_task, req.summary_mode)
    return {"status": "started", "message": "Pipeline triggered in background"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
