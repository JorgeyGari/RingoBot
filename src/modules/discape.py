"""
Discape module for escape room simulation functionality.
"""

import os
import logging
from openpyxl import load_workbook
import discord
from typing import List, Tuple, Dict, Optional

from utils.config import config

logger = logging.getLogger(__name__)


class PaginationView(discord.ui.View):
    """Discord UI view for paginated content."""

    def __init__(self, embeds):
        super().__init__()
        self.embeds = embeds
        self.current = 0

    async def update_page(self, interaction: discord.Interaction):
        """Update the current page display."""
        self.embeds[self.current].set_footer(
            text=f"Página {self.current + 1} de {len(self.embeds)}"
        )
        await interaction.response.edit_message(embed=self.embeds[self.current])

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.blurple)
    async def previous_page(
        self, _: discord.ui.Button, interaction: discord.Interaction
    ):
        """Go to previous page."""
        self.current = (self.current - 1) % len(self.embeds)
        await self.update_page(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.blurple)
    async def next_page(self, _: discord.ui.Button, interaction: discord.Interaction):
        """Go to next page."""
        self.current = (self.current + 1) % len(self.embeds)
        await self.update_page(interaction)


class DiscapeModule:
    """Handles Discape escape room functionality."""

    # Column indices for character sheet
    CHAR_NAME_COL = 0
    CHAR_USER_COL = 1
    CHAR_ROOM_COL = 2
    CHAR_PATH_COL = 3
    CHAR_HAND_COL = 4

    def __init__(self):
        """Initialize the Discape module."""
        self.wb = None
        self._load_workbook()

    def _load_workbook(self):
        """Load the Excel workbook for Discape data."""
        try:
            if os.path.exists(config.DISCAPE_FILE):
                self.wb = load_workbook(filename=config.DISCAPE_FILE)
                logger.info("Discape workbook loaded successfully")
            else:
                logger.warning(f"Discape file not found: {config.DISCAPE_FILE}")
        except Exception as e:
            logger.error(f"Error loading Discape workbook: {e}")

    def get_column_values(self, sheet_name: str, column: int) -> List[str]:
        """Get all values from a specific column in a sheet."""
        if not self.wb:
            return []

        try:
            ws = self.wb[sheet_name]
            return [row[column].value for row in ws]
        except Exception as e:
            logger.error(f"Error getting column values: {e}")
            return []

    def get_row_values(self, sheet_name: str, row: int) -> List[str]:
        """Get all values from a specific row in a sheet."""
        if not self.wb:
            return []

        try:
            ws = self.wb[sheet_name]
            return [cell.value for cell in ws[row]]
        except Exception as e:
            logger.error(f"Error getting row values: {e}")
            return []

    def get_player_location(self, player: str) -> Tuple[str, str]:
        """Get the current location of a player."""
        if not self.wb:
            return (None, None)

        try:
            ws = self.wb["Personajes"]
            player_column_values = self.get_column_values(
                "Personajes", self.CHAR_USER_COL
            )
            player_row = player_column_values.index(player)

            room = ws.cell(row=player_row + 1, column=self.CHAR_ROOM_COL + 1).value
            path = ws.cell(row=player_row + 1, column=self.CHAR_PATH_COL + 1).value

            return (room, path)
        except (ValueError, Exception) as e:
            logger.error(f"Error getting player location: {e}")
            return (None, None)

    def get_player_hand(self, player: str) -> str:
        """Get the item in player's hand."""
        if not self.wb:
            return None

        try:
            ws = self.wb["Personajes"]
            player_column_values = self.get_column_values(
                "Personajes", self.CHAR_USER_COL
            )
            player_row = player_column_values.index(player)

            return ws.cell(row=player_row + 1, column=self.CHAR_HAND_COL + 1).value
        except (ValueError, Exception) as e:
            logger.error(f"Error getting player hand: {e}")
            return None

    def update_player_location(
        self, player: str, location: str, path: Optional[str]
    ) -> None:
        """Update player's location."""
        if not self.wb:
            return

        try:
            ws = self.wb["Personajes"]
            player_row = self.get_column_values("Personajes", self.CHAR_USER_COL).index(
                player
            )

            ws.cell(row=player_row + 1, column=self.CHAR_ROOM_COL + 1, value=location)

            if path == "":
                ws.cell(row=player_row + 1, column=self.CHAR_PATH_COL + 1).value = None
            else:
                ws.cell(row=player_row + 1, column=self.CHAR_PATH_COL + 1, value=path)

            self.wb.save(config.DISCAPE_FILE)
            logger.info(f"Updated player {player} location to {location}, path: {path}")
        except Exception as e:
            logger.error(f"Error updating player location: {e}")

    def get_inventory_dict(self, room: str) -> Dict[str, str]:
        """Get inventory items for a room as a dictionary."""
        if not self.wb:
            return {}

        try:
            ws = self.wb["Inventario"]
            inventory = {}

            for row in ws.iter_rows(min_row=2):
                if (
                    row[0].value is not None
                    and row[1].value is not None
                    and row[2].value == room
                ):
                    inventory[row[0].value] = row[1].value

            return inventory
        except Exception as e:
            logger.error(f"Error getting inventory: {e}")
            return {}

    def join_room(self, player: str, room: str) -> str:
        """Add player to specified room."""
        if not self.wb:
            return "Error: No se pudo cargar el archivo de datos."

        try:
            ws = self.wb["Personajes"]

            for row in ws:
                if row[self.CHAR_USER_COL].value == player:
                    ws.cell(
                        row=row[self.CHAR_NAME_COL].row,
                        column=self.CHAR_ROOM_COL + 1,
                        value=room,
                    )
                    break

            self.wb.save(config.DISCAPE_FILE)
            logger.info(f"Player {player} joined room {room}")
            return f"Te has unido a la sala: {room}."
        except Exception as e:
            logger.error(f"Error joining room: {e}")
            return "Error al unirse a la sala."
