"""
Configuration management for RingoBot.
Centralizes all configuration values and environment variables.
"""

import os
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Configuration class for RingoBot."""

    # Discord Bot Configuration
    TOKEN = os.getenv("TOKEN")
    DEBUG_GUILDS = [429400823395647489, 948015933434253372]

    # Hall of Fame Configuration
    HALL_OF_FAME_CHANNEL_ID = 1273250919110152258
    STAR_EMOJI = "⭐"
    REQUIRED_STARS = 4

    # Quest Configuration
    QUEST_REQUESTS_CHANNEL_ID = 1275940735266328648
    QUEST_CHANNEL_ID_DICT = {"jorgeygari": 1059245948590633123}
    COMPLETED_QUESTS_CHANNEL_ID = 1276207418128207922

    # Database Configuration
    QUEST_DB_PATH = "data/quests.db"
    CHARACTER_DB_PATH = "data/characters.db"

    # File Paths
    DATA_DIR = "data"
    DOWNLOADS_DIR = "downloads"
    DISCAPE_FILE = "data/file.xlsx"
    PRIZES_FILE = "data/prizes.csv"

    # Music Configuration
    YTDL_OPTS = {
        "format": "bestaudio/best",
        "outtmpl": f"{DOWNLOADS_DIR}/%(title)s.%(ext)s",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "noplaylist": True,
        "postprocessor_args": ["-t", "1800"],  # Limit to 30 minutes
    }

    @classmethod
    def validate_config(cls) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not cls.TOKEN:
            errors.append(
                "Discord bot token (TOKEN) not found in environment variables"
            )

        # Create required directories
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.DOWNLOADS_DIR, exist_ok=True)

        return errors


# Create a global config instance
config = Config()
