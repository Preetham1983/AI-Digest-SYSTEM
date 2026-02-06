"""
Interactive Telegram Bot Service
Allows users to control the AI Digest pipeline via Telegram commands.
"""
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from src.config import settings
from src.services.database import db
from src.services.logger import logger
from src.feeds_config import DEFAULT_RSS_FEEDS, DEFAULT_SUBREDDITS

# Global flag to track if pipeline is running
_pipeline_running = False

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available commands."""
    help_text = """
🤖 **AI Digest Bot Commands**

/run - Run the full pipeline (ingest + generate + deliver)
/stop - Stop the bot and shutdown the server
/status - Check if pipeline is running
/prefs - Show current preference settings
/set <key> <on/off> - Toggle a preference
/digest - Show the last generated digest
/sources - List configured news sources
/help - Show this help message

**Keys for /set:**
Sources: `hn`, `reddit`, `rss`
Delivery: `email`, `telegram`
Personas: `genai`, `product`, `finance`

Example: `/set rss on`
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check pipeline status."""
    if _pipeline_running:
        await update.message.reply_text("⏳ Pipeline is currently running...")
    else:
        await update.message.reply_text("✅ Pipeline is idle. Use /run to start.")

async def cmd_prefs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current preferences."""
    await db.init()
    
    pref_keys = [
        "SOURCE_HN_ENABLED", "SOURCE_REDDIT_ENABLED", "SOURCE_RSS_ENABLED",
        "DELIVERY_EMAIL_ENABLED", "DELIVERY_TELEGRAM_ENABLED",
        "PERSONA_GENAI_NEWS_ENABLED", "PERSONA_PRODUCT_IDEAS_ENABLED", "PERSONA_FINANCE_ENABLED"
    ]
    
    lines = ["📋 **Current Preferences:**\n"]
    lines.append("**Sources:**")
    lines.append(f"  • HackerNews: {await db.get_preference('SOURCE_HN_ENABLED', 'true')}")
    lines.append(f"  • Reddit: {await db.get_preference('SOURCE_REDDIT_ENABLED', 'true')}")
    lines.append(f"  • RSS: {await db.get_preference('SOURCE_RSS_ENABLED', 'true')}")
    
    lines.append("\n**Delivery:**")
    lines.append(f"  • Email: {await db.get_preference('DELIVERY_EMAIL_ENABLED', 'true')}")
    lines.append(f"  • Telegram: {await db.get_preference('DELIVERY_TELEGRAM_ENABLED', 'true')}")
    
    lines.append("\n**Personas:**")
    lines.append(f"  • GenAI News: {await db.get_preference('PERSONA_GENAI_NEWS_ENABLED', 'true')}")
    lines.append(f"  • Product Ideas: {await db.get_preference('PERSONA_PRODUCT_IDEAS_ENABLED', 'true')}")
    lines.append(f"  • Finance: {await db.get_preference('PERSONA_FINANCE_ENABLED', 'true')}")
    
    await update.message.reply_text("\n".join(lines), parse_mode='Markdown')

async def cmd_set(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle a preference setting."""
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /set <key> <on/off>\nExample: /set rss on")
        return
    
    key_map = {
        "hn": "SOURCE_HN_ENABLED",
        "reddit": "SOURCE_REDDIT_ENABLED",
        "rss": "SOURCE_RSS_ENABLED",
        "email": "DELIVERY_EMAIL_ENABLED",
        "telegram": "DELIVERY_TELEGRAM_ENABLED",
        "genai": "PERSONA_GENAI_NEWS_ENABLED",
        "product": "PERSONA_PRODUCT_IDEAS_ENABLED",
        "finance": "PERSONA_FINANCE_ENABLED",
    }
    
    key = context.args[0].lower()
    value = context.args[1].lower()
    
    if key not in key_map:
        await update.message.reply_text(f"❌ Unknown key: {key}\nValid keys: {', '.join(key_map.keys())}")
        return
    
    if value not in ["on", "off", "true", "false"]:
        await update.message.reply_text("❌ Value must be 'on' or 'off'")
        return
    
    db_key = key_map[key]
    db_value = "true" if value in ["on", "true"] else "false"
    
    await db.init()
    async with db.get_connection() as conn:
        await conn.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)", (db_key, db_value))
        await conn.commit()
    
    await update.message.reply_text(f"✅ Set `{key}` to `{value}`", parse_mode='Markdown')

async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Run the full pipeline."""
    global _pipeline_running
    
    if _pipeline_running:
        await update.message.reply_text("⏳ Pipeline is already running. Please wait.")
        return
    
    await update.message.reply_text("🚀 Starting pipeline... This may take a few minutes.")
    _pipeline_running = True
    
    try:
        from src.workflows.pipeline import pipeline
        await pipeline.run_pipeline()
        await update.message.reply_text("✅ Pipeline completed successfully! Check your delivery channels.")
    except Exception as e:
        logger.error(f"Telegram /run failed: {e}")
        await update.message.reply_text(f"❌ Pipeline failed: {str(e)[:200]}")
    finally:
        _pipeline_running = False

async def cmd_digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the last generated digest."""
    from datetime import datetime
    from pathlib import Path
    
    digest_path = settings.DATA_DIR / f"digest_{datetime.now().strftime('%Y-%m-%d')}.md"
    
    if not digest_path.exists():
        await update.message.reply_text("📭 No digest found for today. Use /run to generate one.")
        return
    
    content = digest_path.read_text(encoding='utf-8')
    
    # Telegram has 4096 char limit, split if needed
    if len(content) > 4000:
        content = content[:4000] + "\n\n... (truncated)"
    
    await update.message.reply_text(content)

async def cmd_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List configured news sources."""
    lines = ["📰 **Configured Sources:**\n"]
    
    lines.append("**RSS Feeds:**")
    for url in DEFAULT_RSS_FEEDS[:5]:  # Show first 5
        lines.append(f"  • {url[:50]}...")
    if len(DEFAULT_RSS_FEEDS) > 5:
        lines.append(f"  ... and {len(DEFAULT_RSS_FEEDS) - 5} more")
    
    lines.append("\n**Reddit Subreddits:**")
    for url in DEFAULT_SUBREDDITS:
        lines.append(f"  • {url}")
    
    lines.append("\n**HackerNews:**")
    lines.append("  • Top Stories & Show HN")
    
    await update.message.reply_text("\n".join(lines), parse_mode='Markdown')

async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop the bot and shutdown the server."""
    import os
    import signal
    
    await update.message.reply_text("🛑 Shutting down bot and server... Goodbye!")
    logger.info("Received /stop command. Shutting down...")
    
    # Give time for the message to be sent
    await asyncio.sleep(1)
    
    # Send SIGINT to gracefully shutdown
    os.kill(os.getpid(), signal.SIGINT)

def create_telegram_bot() -> Application:
    """Create and configure the Telegram bot application."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Bot will not start.")
        return None
    
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    # Register command handlers
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("start", cmd_help))  # Same as help
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("prefs", cmd_prefs))
    app.add_handler(CommandHandler("set", cmd_set))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(CommandHandler("digest", cmd_digest))
    app.add_handler(CommandHandler("sources", cmd_sources))
    app.add_handler(CommandHandler("stop", cmd_stop))
    
    logger.info("Telegram Bot configured with command handlers.")
    return app

async def start_bot_polling():
    """Start the bot in polling mode (for standalone use)."""
    app = create_telegram_bot()
    if app:
        logger.info("Starting Telegram Bot polling...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        # Keep running
        while True:
            await asyncio.sleep(1)
