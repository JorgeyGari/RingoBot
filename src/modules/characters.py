"""
Characters module for character registration and points tracking.
"""

import sqlite3
import logging
from typing import List, Tuple, Optional

from utils.config import config

logger = logging.getLogger(__name__)


class CharactersModule:
    """Handles character registration and points tracking functionality."""

    CREATE_TABLE_CHARACTERS = """CREATE TABLE IF NOT EXISTS characters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        discord_id TEXT UNIQUE NOT NULL,
        character_name TEXT NOT NULL,
        points INTEGER DEFAULT 0,
        guild_id TEXT,
        picture_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );"""

    CREATE_TABLE_POINT_HISTORY = """CREATE TABLE IF NOT EXISTS point_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        character_id INTEGER,
        points_change INTEGER,
        reason TEXT,
        admin_id TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (character_id) REFERENCES characters (id)
    );"""

    def __init__(self):
        """Initialize the characters module."""
        self.db_path = config.CHARACTER_DB_PATH
        # ponytail: one shared connection, same deal as QuestsModule. sqlite3
        # serializes access itself and every caller runs on the bot's event
        # loop thread. Pool it if writes ever move off that thread and contend.
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self) -> None:
        """Create the required tables."""
        try:
            with self.conn:
                self.conn.execute(self.CREATE_TABLE_CHARACTERS)
                self.conn.execute(self.CREATE_TABLE_POINT_HISTORY)
            logger.info("Character tables created/verified successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")

    def register_character(
        self, discord_id: str, character_name: str, guild_id: str, picture_url: str = None
    ) -> bool:
        """Register a new character."""
        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO characters (discord_id, character_name, guild_id, picture_url)
                    VALUES (?, ?, ?, ?)
                """,
                    (discord_id, character_name, guild_id, picture_url),
                )
            logger.info(f"Character {character_name} registered for user {discord_id}")
            return True
        except sqlite3.IntegrityError:
            logger.warning(
                f"Character registration failed - user {discord_id} already has a character"
            )
            return False
        except Exception as e:
            logger.error(f"Error registering character: {e}")
            return False

    def get_character(self, discord_id: str) -> Optional[Tuple]:
        """Get character info by Discord ID."""
        try:
            return self.conn.execute(
                """
                SELECT id, discord_id, character_name, points, guild_id, picture_url, created_at, updated_at
                FROM characters WHERE discord_id = ?
            """,
                (discord_id,),
            ).fetchone()
        except Exception as e:
            logger.error(f"Error getting character: {e}")
            return None

    def update_picture(self, discord_id: str, picture_url: str) -> bool:
        """Update a character's picture URL."""
        try:
            with self.conn:
                cursor = self.conn.execute(
                    """
                    UPDATE characters
                    SET picture_url = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE discord_id = ?
                """,
                    (picture_url, discord_id),
                )

            if cursor.rowcount > 0:
                logger.info(f"Picture updated for character {discord_id}")
                return True
            else:
                logger.warning(f"No character found for {discord_id} to update picture")
                return False
        except Exception as e:
            logger.error(f"Error updating character picture: {e}")
            return False

    def update_character_name(self, discord_id: str, new_name: str) -> bool:
        """Update a character's name."""
        try:
            with self.conn:
                cursor = self.conn.execute(
                    """
                    UPDATE characters
                    SET character_name = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE discord_id = ?
                """,
                    (new_name, discord_id),
                )

            if cursor.rowcount > 0:
                logger.info(f"Name updated for character {discord_id} to {new_name}")
                return True
            else:
                logger.warning(f"No character found for {discord_id} to update name")
                return False
        except Exception as e:
            logger.error(f"Error updating character name: {e}")
            return False

    def update_character_info(self, discord_id: str, new_name: str = None, new_picture_url: str = None) -> bool:
        """Update character name and/or picture in a single operation."""
        try:
            # Build dynamic query based on what needs to be updated
            updates = []
            params = []

            if new_name is not None:
                updates.append("character_name = ?")
                params.append(new_name)

            if new_picture_url is not None:
                updates.append("picture_url = ?")
                params.append(new_picture_url)

            if not updates:
                return True  # Nothing to update

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(discord_id)

            query = f"UPDATE characters SET {', '.join(updates)} WHERE discord_id = ?"
            with self.conn:
                cursor = self.conn.execute(query, params)

            if cursor.rowcount > 0:
                changes = []
                if new_name: changes.append(f"name to '{new_name}'")
                if new_picture_url: changes.append("picture")
                logger.info(f"Updated character {discord_id}: {', '.join(changes)}")
                return True
            else:
                logger.warning(f"No character found for {discord_id} to update")
                return False
        except Exception as e:
            logger.error(f"Error updating character info: {e}")
            return False

    def update_points(
        self, discord_id: str, points_change: int, reason: str = "", admin_id: str = ""
    ) -> bool:
        """Add or subtract points from a character."""
        try:
            # Get current character info
            result = self.conn.execute(
                """
                SELECT id, points FROM characters WHERE discord_id = ?
            """,
                (discord_id,),
            ).fetchone()

            if not result:
                logger.warning(
                    f"Cannot update points - character not found for user {discord_id}"
                )
                return False

            char_id, current_points = result
            new_points = max(
                0, current_points + points_change
            )  # Prevent negative points

            # Points update and its history row share one transaction: the
            # `with` block rolls both back if either statement fails.
            with self.conn:
                self.conn.execute(
                    """
                    UPDATE characters
                    SET points = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE discord_id = ?
                """,
                    (new_points, discord_id),
                )
                self.conn.execute(
                    """
                    INSERT INTO point_history (character_id, points_change, reason, admin_id)
                    VALUES (?, ?, ?, ?)
                """,
                    (char_id, points_change, reason, admin_id),
                )

            logger.info(
                f"Points updated for {discord_id}: {points_change} PC (reason: {reason})"
            )
            return True
        except Exception as e:
            logger.error(f"Error updating points: {e}")
            return False

    def get_leaderboard(self, guild_id: str = None, limit: int = 10) -> List[Tuple]:
        """Get characters sorted by points (highest first)."""
        try:
            if guild_id:
                return self.conn.execute(
                    """
                    SELECT character_name, points, discord_id
                    FROM characters
                    WHERE guild_id = ?
                    ORDER BY points DESC
                    LIMIT ?
                """,
                    (guild_id, limit),
                ).fetchall()

            return self.conn.execute(
                """
                SELECT character_name, points, discord_id
                FROM characters
                ORDER BY points DESC
                LIMIT ?
            """,
                (limit,),
            ).fetchall()
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []

    def get_point_history(self, discord_id: str, limit: int = 10) -> List[Tuple]:
        """Get point history for a character."""
        try:
            return self.conn.execute(
                """
                SELECT ph.points_change, ph.reason, ph.admin_id, ph.timestamp
                FROM point_history ph
                JOIN characters c ON ph.character_id = c.id
                WHERE c.discord_id = ?
                ORDER BY ph.timestamp DESC
                LIMIT ?
            """,
                (discord_id, limit),
            ).fetchall()
        except Exception as e:
            logger.error(f"Error getting point history: {e}")
            return []

    def delete_character(self, discord_id: str) -> bool:
        """Delete a character and their history."""
        try:
            # Get character ID first
            character = self.get_character(discord_id)
            if not character:
                return False

            char_id = character[0]

            with self.conn:
                # Delete history first (foreign key constraint)
                self.conn.execute(
                    "DELETE FROM point_history WHERE character_id = ?", (char_id,)
                )
                self.conn.execute(
                    "DELETE FROM characters WHERE discord_id = ?", (discord_id,)
                )

            logger.info(f"Character deleted for user {discord_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting character: {e}")
            return False

    def get_all_characters(self, guild_id: str = None) -> List[Tuple]:
        """Get all characters, optionally filtered by guild."""
        try:
            if guild_id:
                return self.conn.execute(
                    """
                    SELECT character_name, points, discord_id, created_at
                    FROM characters
                    WHERE guild_id = ?
                    ORDER BY character_name
                """,
                    (guild_id,),
                ).fetchall()

            return self.conn.execute(
                """
                SELECT character_name, points, discord_id, created_at
                FROM characters
                ORDER BY character_name
            """
            ).fetchall()
        except Exception as e:
            logger.error(f"Error getting all characters: {e}")
            return []
