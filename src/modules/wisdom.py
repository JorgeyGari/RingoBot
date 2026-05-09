"""
Wisdom module for handling wisdom quotes and user submissions.
"""

import csv
import json
import logging
import random
import asyncio
import unicodedata
import re
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime
import discord
from discord.ui import View, Select

logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """Normalize text for pattern matching: lowercase + accent removal."""
    nfkd = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


_WISDOM_TRIGGER = re.compile(r"\bque\s+opinas\b.*\bringobot\b")


class WisdomSelect(Select):
    """Select menu for deleting wisdoms."""

    def __init__(self, wisdoms: List[Dict[str, str]], user_name: str, module: "WisdomModule"):
        self.module = module
        self.user_name = user_name
        self.wisdom_map = {}
        options = []
        idx = 0
        for wisdom in wisdoms:
            if wisdom.get("added_by") == user_name:
                label = wisdom["text"][:100]
                value = str(idx)
                self.wisdom_map[value] = wisdom["text"]
                options.append(discord.SelectOption(label=label, value=value))
                idx += 1

        super().__init__(
            placeholder="Elige una sabiduría para eliminar",
            min_values=1,
            max_values=1,
            options=options[:25],
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle wisdom deletion."""
        selected_idx = self.values[0]
        selected_text = self.wisdom_map[selected_idx]
        if self.module.delete(selected_text, self.user_name):
            await interaction.response.edit_message(
                content=f'Sabiduría eliminada: «{selected_text}».',
                view=None,
            )
        else:
            await interaction.response.edit_message(
                content="No se pudo eliminar la sabiduría.",
                view=None,
            )


class WisdomDeleteView(View):
    """View containing the wisdom select menu."""

    def __init__(self, wisdoms: List[Dict[str, str]], user_name: str, module: "WisdomModule"):
        super().__init__(timeout=60)
        self.add_item(WisdomSelect(wisdoms, user_name, module))


class WisdomModule:
    """Handles wisdom storage, retrieval, and user submissions."""

    def __init__(self, csv_path: str):
        """Initialize the wisdom module and load existing wisdoms."""
        self._path = Path(csv_path)
        self._wisdoms: List[Dict[str, str]] = []
        self._load()
        logger.info(f"WisdomModule initialized with {len(self._wisdoms)} wisdoms")

    def _load(self):
        """Load wisdoms from JSON, with CSV fallback and auto-migration."""
        if self._path.exists():
            try:
                self._load_json()
            except (json.JSONDecodeError, Exception):
                logger.info("JSON file not valid or doesn't exist, skipping")
                self._wisdoms = []
        else:
            csv_path = self._path.parent / "wisdoms.csv"
            if csv_path.exists():
                logger.info("JSON not found, attempting CSV migration")
                self._migrate_csv_to_json(csv_path)
            else:
                logger.info("No wisdoms file found, starting fresh")
                self._wisdoms = []


    def _migrate_csv_to_json(self, csv_path: Path):
        """Migrate wisdoms from CSV to JSON format."""
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                wisdoms = []
                for row in reader:
                    row.setdefault("last_shown", "")
                    wisdoms.append(row)
            self._wisdoms = wisdoms
            self._save_json_sync()
            logger.info(f"Migrated {len(wisdoms)} wisdoms from CSV to JSON")
        except Exception as e:
            logger.error(f"Error migrating CSV to JSON: {e}")
            self._wisdoms = []

    def _load_json(self):
        """Load wisdoms from JSON file."""
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._wisdoms = json.load(f)
            logger.info(f"Loaded {len(self._wisdoms)} wisdoms from JSON")
        except Exception as e:
            logger.error(f"Error loading wisdoms from JSON: {e}")
            self._wisdoms = []

    def _save_json_sync(self):
        """Save wisdoms to JSON file synchronously."""
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._wisdoms, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving wisdoms to JSON: {e}", exc_info=True)
            raise

    def _calculate_probability(self, wisdom_text: str) -> float:
        """Calculate the selection probability % for a wisdom based on recency weights."""
        if not self._wisdoms:
            return 0.0

        weights = []
        target_idx = None
        for idx, wisdom in enumerate(self._wisdoms):
            if wisdom["text"] == wisdom_text:
                target_idx = idx
            last_shown = wisdom.get("last_shown", "")
            if not last_shown:
                weight = 2_592_000  # 30 days in seconds
            else:
                try:
                    last_shown_dt = datetime.fromisoformat(last_shown)
                    seconds_since = (datetime.now() - last_shown_dt).total_seconds()
                    weight = max(1, int(seconds_since) + 1)
                except ValueError:
                    weight = 2_592_000
            weights.append(weight)

        if target_idx is None:
            return 0.0

        total_weight = sum(weights)
        return (weights[target_idx] / total_weight) * 100.0

    async def get_random(self) -> Optional[str]:
        """Get a weighted random wisdom, preferring ones not recently shown."""
        if not self._wisdoms:
            return None

        weights = []
        for wisdom in self._wisdoms:
            last_shown = wisdom.get("last_shown", "")
            if not last_shown:
                weight = 2_592_000  # 30 days in seconds
            else:
                try:
                    last_shown_dt = datetime.fromisoformat(last_shown)
                    seconds_since = (datetime.now() - last_shown_dt).total_seconds()
                    weight = max(1, int(seconds_since) + 1)
                except ValueError:
                    weight = 2_592_000
            weights.append(weight)

        chosen = random.choices(self._wisdoms, weights=weights, k=1)[0]
        chosen["last_shown"] = datetime.now().isoformat()
        self._save_json_sync()

        return chosen["text"]

    async def add(self, text: str, user: str) -> float:
        """Add a new wisdom and return its selection probability %."""
        wisdom_entry = {
            "text": text,
            "date_added": datetime.now().isoformat(),
            "added_by": user,
            "last_shown": "",
        }
        self._wisdoms.append(wisdom_entry)
        self._save_json_sync()

        probability = self._calculate_probability(text)
        logger.info(f"Added wisdom by {user}: {text[:50]}...")
        return probability

    def delete(self, text: str, user_name: str) -> bool:
        """Remove a wisdom owned by the user. Returns True if deleted."""
        for wisdom in self._wisdoms:
            if wisdom["text"] == text and wisdom.get("added_by") == user_name:
                self._wisdoms.remove(wisdom)
                self._save_json_sync()
                logger.info(f"Deleted wisdom by {user_name}: {text[:50]}...")
                return True
        return False

    async def handle_delete_command(self, ctx: discord.ApplicationContext):
        """Show a select menu with the user's wisdoms for deletion."""
        try:
            user_wisdoms = [w for w in self._wisdoms if w.get("added_by") == ctx.user.name]
            if not user_wisdoms:
                await ctx.respond(
                    "No tienes ninguna sabiduría registrada.",
                    ephemeral=True,
                )
                return

            view = WisdomDeleteView(self._wisdoms, ctx.user.name, self)
            await ctx.respond(
                "Selecciona una sabiduría para eliminar:",
                view=view,
                ephemeral=True,
            )
        except Exception as e:
            logger.error(f"Error handling delete command: {e}", exc_info=True)
            await ctx.respond(
                "Error al procesar tu solicitud. Inténtalo de nuevo.",
                ephemeral=True,
            )

    async def handle_wisdom_command(self, ctx: discord.ApplicationContext, sabiduría: Optional[str]):
        """Handle the /sabiduria slash command."""
        try:
            if sabiduría:
                # User is submitting a new wisdom
                user_name = ctx.user.name
                probability = await self.add(sabiduría, user_name)
                confirmation = (
                    f'Has registrado la sabiduría n.º {len(self._wisdoms)}:\n'
                    f'> {sabiduría}\n'
                    f'-# Probabilidad de aparecer: {probability:.2f} %.'
                )
                await ctx.respond(confirmation, ephemeral=True)
            else:
                # User is requesting a random wisdom
                wisdom = await self.get_random()
                if wisdom:
                    await ctx.respond(f'{wisdom}')
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
            wisdom = await self.get_random()
            if wisdom:
                await message.reply(f'{wisdom}', mention_author=False)
        except Exception as e:
            logger.error(f"Error handling wisdom message: {e}")
