"""
Wisdom module for handling wisdom quotes and user submissions.
"""

import csv
import logging
import random
import asyncio
import unicodedata
import re
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import discord

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """Normalize text for pattern matching: lowercase + accent removal."""
    nfkd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


_WISDOM_TRIGGER = re.compile(r"\bque\s+opinas\b.*\bringobot\b")


class WisdomModule:
    """Handles wisdom storage, retrieval, and user submissions."""

    def __init__(self, csv_path: str):
        """Initialize the wisdom module and load existing wisdoms."""
        self._path = Path(csv_path)
        self._wisdoms: List[Dict[str, str]] = []
        self._load()
        logger.info(f"WisdomModule initialized with {len(self._wisdoms)} wisdoms")

    def _load(self):
        """Load wisdoms from CSV file, creating it if it doesn't exist."""
        if not self._path.exists():
            self._create_csv()
        else:
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    self._wisdoms = list(reader) if reader else []
                logger.info(f"Loaded {len(self._wisdoms)} wisdoms from CSV")
            except Exception as e:
                logger.error(f"Error loading wisdoms from CSV: {e}")
                self._wisdoms = []

    def _create_csv(self):
        """Create the CSV file with headers."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["text", "date_added", "added_by"])
                writer.writeheader()
            logger.info(f"Created wisdoms CSV at {self._path}")
        except Exception as e:
            logger.error(f"Error creating wisdoms CSV: {e}")

    def _save_csv_sync(self):
        """Save wisdoms to CSV file synchronously."""
        try:
            with open(self._path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["text", "date_added", "added_by"])
                writer.writeheader()
                writer.writerows(self._wisdoms)
        except Exception as e:
            logger.error(f"Error saving wisdoms to CSV: {e}", exc_info=True)
            raise

    def get_random(self) -> Optional[str]:
        """Get a random wisdom text."""
        if not self._wisdoms:
            return None
        return random.choice(self._wisdoms)["text"]

    async def add(self, text: str, user: str) -> float:
        """Add a new wisdom and return its probability percentage."""
        wisdom_entry = {
            "text": text,
            "date_added": datetime.now().isoformat(),
            "added_by": user,
        }
        self._wisdoms.append(wisdom_entry)
        self._save_csv_sync()

        probability = 100.0 / len(self._wisdoms)
        logger.info(f"Added wisdom by {user}: {text[:50]}...")
        return probability

    async def handle_wisdom_command(self, ctx: discord.ApplicationContext, sabiduría: Optional[str]):
        """Handle the /sabiduria slash command."""
        try:
            if sabiduría:
                # User is submitting a new wisdom
                user_name = ctx.user.name
                probability = await self.add(sabiduría, user_name)
                confirmation = (
                    f'Has registrado la sabiduría: «{sabiduría}».\n'
                    f'Tiene un {probability:.2f} % de probabilidades de aparecer.'
                )
                await ctx.respond(confirmation, ephemeral=True)
            else:
                # User is requesting a random wisdom
                wisdom = self.get_random()
                if wisdom:
                    await ctx.respond(f'💭 {wisdom}')
                else:
                    await ctx.respond(
                        "Aún no tengo sabiduría que compartir contigo. ¿Tienes alguna para mí?",
                        ephemeral=True
                    )
        except Exception as e:
            logger.error(f"Error handling wisdom command: {e}", exc_info=True)
            await ctx.respond(
                "Error al procesar tu sabiduría. Inténtalo de nuevo.",
                ephemeral=True,
            )

    async def handle_wisdom_message(self, message: discord.Message):
        """Handle the message trigger for wisdom queries."""
        try:
            wisdom = self.get_random()
            if wisdom:
                await message.reply(f'{wisdom}', mention_author=False)
        except Exception as e:
            logger.error(f"Error handling wisdom message: {e}")
