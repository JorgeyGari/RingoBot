"""
Quests module for quest management functionality.
"""

import sqlite3
import logging
from typing import List, Tuple, Optional

from utils.config import config

logger = logging.getLogger(__name__)


class QuestsModule:
    """Handles quest management functionality."""

    CREATE_TABLE_QUESTS = """CREATE TABLE IF NOT EXISTS quests (
        id integer PRIMARY KEY,
        player text NOT NULL,
        description text NULL,
        reward text NULL
    );"""

    def __init__(self):
        """Initialize the quests module."""
        self.db_path = config.QUEST_DB_PATH
        self._create_table()

    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Create database connection."""
        try:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            logger.info(f"Connected to quest database: {self.db_path}")
            return conn
        except sqlite3.Error as e:
            logger.error(f"Error connecting to database: {e}")
            return None

    def _create_table(self) -> None:
        """Create the quests table if it doesn't exist."""
        conn = self._create_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()
            cursor.execute(self.CREATE_TABLE_QUESTS)
            conn.commit()
            logger.info("Quests table created/verified")
        except sqlite3.Error as e:
            logger.error(f"Error creating table: {e}")
        finally:
            conn.close()

    def create_request(self, player: str) -> int:
        """
        Create a new quest request for a player.

        Args:
            player: Player identifier

        Returns:
            Quest ID if successful, -1 if player already has pending request
        """
        conn = self._create_connection()
        if not conn:
            return -1

        try:
            cursor = conn.cursor()

            # Check for existing pending request
            existing_sql = """SELECT * FROM quests WHERE player=? AND description IS NULL AND reward IS NULL"""
            cursor.execute(existing_sql, (player,))
            existing_record = cursor.fetchone()

            if existing_record:
                logger.info(f"Player {player} already has pending quest request")
                return -1

            # Insert new request
            sql = """INSERT INTO quests(player, description, reward) VALUES(?,?,?)"""
            cursor.execute(sql, (player, None, None))
            conn.commit()

            quest_id = cursor.lastrowid
            logger.info(f"Created quest request {quest_id} for player {player}")
            return quest_id

        except sqlite3.Error as e:
            logger.error(f"Error creating quest request: {e}")
            return -1
        finally:
            conn.close()

    def get_users_with_pending_requests(self) -> List[str]:
        """Get list of users with pending quest requests."""
        conn = self._create_connection()
        if not conn:
            return []

        try:
            sql = """SELECT player FROM quests WHERE description IS NULL AND reward IS NULL"""
            cursor = conn.cursor()
            cursor.execute(sql)
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error getting pending requests: {e}")
            return []
        finally:
            conn.close()

    def get_user_request_id(self, player: str) -> Optional[int]:
        """Get the quest request ID for a player."""
        conn = self._create_connection()
        if not conn:
            return None

        try:
            sql = """SELECT id FROM quests WHERE player=? AND description IS NULL AND reward IS NULL"""
            cursor = conn.cursor()
            cursor.execute(sql, (player,))
            row = cursor.fetchone()
            return row[0] if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting user request ID: {e}")
            return None
        finally:
            conn.close()

    def get_user_active_quests(self, player: str) -> List[Tuple]:
        """Get active quests for a player."""
        conn = self._create_connection()
        if not conn:
            return []

        try:
            sql = """SELECT * FROM quests WHERE player=? AND description IS NOT NULL AND reward IS NOT NULL"""
            cursor = conn.cursor()
            cursor.execute(sql, (player,))
            rows = cursor.fetchall()
            return rows
        except sqlite3.Error as e:
            logger.error(f"Error getting active quests: {e}")
            return []
        finally:
            conn.close()

    def update_request(self, player: str, description: str, reward: str) -> bool:
        """
        Update a quest request with description and reward.

        Args:
            player: Player identifier
            description: Quest description
            reward: Quest reward

        Returns:
            True if successful, False otherwise
        """
        conn = self._create_connection()
        if not conn:
            return False

        try:
            request_id = self.get_user_request_id(player)
            if not request_id:
                return False

            sql = """UPDATE quests SET description = ?, reward = ? WHERE id = ?"""
            cursor = conn.cursor()
            cursor.execute(sql, (description, reward, request_id))
            conn.commit()

            logger.info(f"Updated quest {request_id} for player {player}")
            return True

        except sqlite3.Error as e:
            logger.error(f"Error updating quest request: {e}")
            return False
        finally:
            conn.close()
