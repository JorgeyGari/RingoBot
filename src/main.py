#!/usr/bin/env python3
"""
RingoBot - Discord Bot for RINGOS 2.0
Main entry point for the application.
"""

import os
import logging

from bot.ringobot import RingoBot


def main():
    """Main entry point for RingoBot."""
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("logs/ringobot.log"), logging.StreamHandler()],
    )

    RingoBot().run()


if __name__ == "__main__":
    main()
