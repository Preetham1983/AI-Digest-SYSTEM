import asyncio
import sys
from src.workflows.pipeline import pipeline
from src.services.database import db
from src.services.logger import logger

async def main():
    print(">>> Starting Debug Pipeline Run...")
    # Initialize DB logic
    await db.init()
    
    # Run Generation Only (since we likely have data)
    # But let's run full to check dedup in ingestion too
    print("--- Phase 1: Ingestion ---")
    await pipeline.run_ingestion()
    
    print("\n--- Phase 2: Generation (Batch Mode) ---")
    await pipeline.run_generation(summary_mode=True)
    
    print("\n[OK] Run Complete. Check logs/console for 'Batch Evaluating'.")

if __name__ == "__main__":
    # Configure logger to print to stderr so we see it
    logger.add(sys.stderr, level="INFO")
    asyncio.run(main())
