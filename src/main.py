#!/usr/bin/env python3
"""
RingoBot - Discord Bot for RINGOS 2.0
Main entry point for the application.
"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from bot.ringobot import RingoBot


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("logs/ringobot.log"), logging.StreamHandler()],
    )


def main():
    """Main entry point for RingoBot."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)

    # Setup logging
    setup_logging()

    # Create and run the bot
    bot = RingoBot()
    bot.run()


if __name__ == "__main__":
    main()
