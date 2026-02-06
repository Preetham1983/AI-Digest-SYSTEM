import asyncio
import sys
from src.workflows.pipeline import pipeline
from src.services.logger import logger

def main():
    try:
        asyncio.run(pipeline.run_pipeline())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
