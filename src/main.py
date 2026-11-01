#!/usr/bin/env python3
"""
RingoBot - Discord Bot for RINGOS 2.0
Main entry point for the application.
"""

import logging
import os

from bot.ringobot import RingoBot


def main():
    """Main entry point for RingoBot."""
    try:
        os.makedirs("logs", exist_ok=True)
    except OSError as e:
        raise SystemExit(f"No se pudo crear el directorio de logs: {e}") from e
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("logs/ringobot.log"), logging.StreamHandler()],
    )

    RingoBot().run()


if __name__ == "__main__":
    main()
