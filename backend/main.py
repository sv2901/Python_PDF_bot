"""
Main entry point - Runs both FastAPI health server and Telegram bot
"""

import asyncio
import os
import sys
import signal
import logging
import threading
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_health_server():
    """Run FastAPI health check server in a thread."""
    from server import app
    
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8001,
        log_level="warning"
    )
    server = uvicorn.Server(config)
    server.run()


def run_telegram_bot():
    """Run Telegram bot."""
    from bot import run_bot
    run_bot()


def main():
    """Main entry point."""
    # Check for required environment variables
    required_vars = ["TELEGRAM_API_ID", "TELEGRAM_API_HASH", "TELEGRAM_BOT_TOKEN"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    
    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.info("Please set: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    
    logger.info("Starting PDF Bot System...")
    
    # Start health server in background thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()
    logger.info("Health server started on port 8001")
    
    # Run bot in main thread
    logger.info("Starting Telegram bot...")
    run_telegram_bot()


if __name__ == "__main__":
    main()
