import sys
from loguru import logger
from src.config import settings

def setup_logging():
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    # Add file logging
    log_file = settings.DATA_DIR / "app.log"
    logger.add(log_file, rotation="10 MB", level="DEBUG")

setup_logging()
