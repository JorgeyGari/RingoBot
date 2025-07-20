"""
Characters module for character registration and points tracking.
"""

import sqlite3
import logging
from typing import List, Tuple, Optional, Dict
from datetime import datetime

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
        self._create_tables()

    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Create a new database connection."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.execute("PRAGMA busy_timeout=10000")
            return conn
        except Exception as e:
            logger.error(f"Error creating connection: {e}")
            return None

    def _create_tables(self) -> None:
        """Create the required tables."""
        conn = self._create_connection()
        if not conn:
            logger.error("Failed to create connection for table creation")
            return

        try:
            cursor = conn.cursor()
            cursor.execute(self.CREATE_TABLE_CHARACTERS)
            cursor.execute(self.CREATE_TABLE_POINT_HISTORY)
            conn.commit()
            logger.info("Character tables created/verified successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
        finally:
            conn.close()

    def register_character(
        self, discord_id: str, character_name: str, guild_id: str, picture_url: str = None
    ) -> bool:
        """Register a new character."""
        conn = self._create_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO characters (discord_id, character_name, guild_id, picture_url)
                VALUES (?, ?, ?, ?)
            """,
                (discord_id, character_name, guild_id, picture_url),
            )
            conn.commit()
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
        finally:
            conn.close()

    def get_character(self, discord_id: str) -> Optional[Tuple]:
        """Get character info by Discord ID."""
        conn = self._create_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, discord_id, character_name, points, guild_id, picture_url, created_at, updated_at
                FROM characters WHERE discord_id = ?
            """,
                (discord_id,),
            )
            return cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting character: {e}")
            return None
        finally:
            conn.close()

    def update_picture(self, discord_id: str, picture_url: str) -> bool:
        """Update a character's picture URL."""
        conn = self._create_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE characters 
                SET picture_url = ?, updated_at = CURRENT_TIMESTAMP
                WHERE discord_id = ?
            """,
                (picture_url, discord_id),
            )
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Picture updated for character {discord_id}")
                return True
            else:
                logger.warning(f"No character found for {discord_id} to update picture")
                return False
        except Exception as e:
            logger.error(f"Error updating character picture: {e}")
            return False
        finally:
            conn.close()

    def update_character_name(self, discord_id: str, new_name: str) -> bool:
        """Update a character's name."""
        conn = self._create_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE characters 
                SET character_name = ?, updated_at = CURRENT_TIMESTAMP
                WHERE discord_id = ?
            """,
                (new_name, discord_id),
            )
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Name updated for character {discord_id} to {new_name}")
                return True
            else:
                logger.warning(f"No character found for {discord_id} to update name")
                return False
        except Exception as e:
            logger.error(f"Error updating character name: {e}")
            return False
        finally:
            conn.close()

    def update_character_info(self, discord_id: str, new_name: str = None, new_picture_url: str = None) -> bool:
        """Update character name and/or picture in a single operation."""
        conn = self._create_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            
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
            cursor.execute(query, params)
            conn.commit()
            
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
        finally:
            conn.close()

    def update_points(
        self, discord_id: str, points_change: int, reason: str = "", admin_id: str = ""
    ) -> bool:
        """Add or subtract points from a character."""
        conn = self._create_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()

            # Get current character info
            cursor.execute(
                """
                SELECT id, points FROM characters WHERE discord_id = ?
            """,
                (discord_id,),
            )
            result = cursor.fetchone()

            if not result:
                logger.warning(
                    f"Cannot update points - character not found for user {discord_id}"
                )
                return False

            char_id, current_points = result
            new_points = max(
                0, current_points + points_change
            )  # Prevent negative points

            # Update character points
            cursor.execute(
                """
                UPDATE characters 
                SET points = ?, updated_at = CURRENT_TIMESTAMP
                WHERE discord_id = ?
            """,
                (new_points, discord_id),
            )

            # Record in history
            cursor.execute(
                """
                INSERT INTO point_history (character_id, points_change, reason, admin_id)
                VALUES (?, ?, ?, ?)
            """,
                (char_id, points_change, reason, admin_id),
            )

            conn.commit()
            logger.info(
                f"Points updated for {discord_id}: {points_change} PC (reason: {reason})"
            )
            return True
        except Exception as e:
            logger.error(f"Error updating points: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_leaderboard(self, guild_id: str = None, limit: int = 10) -> List[Tuple]:
        """Get characters sorted by points (highest first)."""
        conn = self._create_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            if guild_id:
                cursor.execute(
                    """
                    SELECT character_name, points, discord_id
                    FROM characters 
                    WHERE guild_id = ?
                    ORDER BY points DESC 
                    LIMIT ?
                """,
                    (guild_id, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT character_name, points, discord_id
                    FROM characters 
                    ORDER BY points DESC 
                    LIMIT ?
                """,
                    (limit,),
                )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
        finally:
            conn.close()

    def get_point_history(self, discord_id: str, limit: int = 10) -> List[Tuple]:
        """Get point history for a character."""
        conn = self._create_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT ph.points_change, ph.reason, ph.admin_id, ph.timestamp
                FROM point_history ph
                JOIN characters c ON ph.character_id = c.id
                WHERE c.discord_id = ?
                ORDER BY ph.timestamp DESC
                LIMIT ?
            """,
                (discord_id, limit),
            )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting point history: {e}")
            return []
        finally:
            conn.close()

    def delete_character(self, discord_id: str) -> bool:
        """Delete a character and their history."""
        conn = self._create_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()

            # Get character ID first
            character = self.get_character(discord_id)
            if not character:
                return False

            char_id = character[0]

            # Delete history first (foreign key constraint)
            cursor.execute(
                "DELETE FROM point_history WHERE character_id = ?", (char_id,)
            )

            # Delete character
            cursor.execute("DELETE FROM characters WHERE discord_id = ?", (discord_id,))

            conn.commit()
            logger.info(f"Character deleted for user {discord_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting character: {e}")
            return False
        finally:
            conn.close()

    def get_all_characters(self, guild_id: str = None) -> List[Tuple]:
        """Get all characters, optionally filtered by guild."""
        conn = self._create_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            if guild_id:
                cursor.execute(
                    """
                    SELECT character_name, points, discord_id, created_at
                    FROM characters 
                    WHERE guild_id = ?
                    ORDER BY character_name
                """,
                    (guild_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT character_name, points, discord_id, created_at
                    FROM characters 
                    ORDER BY character_name
                """
                )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting all characters: {e}")
            return []
        finally:
            conn.close()
