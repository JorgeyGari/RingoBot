"""
Gacha module for prize rolling functionality.
Handles item management, rolling mechanics, and inventory system.
"""

import csv
import random
import sqlite3
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from utils.config import config

logger = logging.getLogger(__name__)


@dataclass
class Prize:
    """Represents a gacha prize."""

    name: str
    description: str
    rareness: int
    special_character: Optional[str] = None


@dataclass
class RollResult:
    """Represents the result of a gacha roll."""

    prizes: List[Prize]
    cost: int
    roll_type: str  # "single", "multi5", "multi10"
    guaranteed_used: bool = False


class GachaModule:
    """Handles gacha prize rolling functionality."""

    # Gacha configuration
    SINGLE_ROLL_COST = 10
    MULTI_ROLL_5_COST = 50
    MULTI_ROLL_10_COST = 100

    # Rarity probabilities (for single rolls without guarantees)
    RARITY_WEIGHTS = {
        1: 70,  # Common - 70%
        2: 25,  # Rare - 25%
        3: 5,  # Legendary - 5%
    }

    # Special item chance for rarity 3 pulls
    SPECIAL_ITEM_CHANCE = 0.5

    # Database table creation queries
    CREATE_TABLE_INVENTORY = """CREATE TABLE IF NOT EXISTS user_inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        discord_id TEXT NOT NULL,
        item_name TEXT NOT NULL,
        quantity INTEGER DEFAULT 1,
        obtained_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (discord_id) REFERENCES characters (discord_id)
    );"""

    CREATE_TABLE_ROLL_HISTORY = """CREATE TABLE IF NOT EXISTS roll_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        discord_id TEXT NOT NULL,
        roll_type TEXT NOT NULL,
        cost INTEGER NOT NULL,
        items_obtained TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (discord_id) REFERENCES characters (discord_id)
    );"""

    def __init__(self):
        """Initialize the gacha module."""
        self.db_path = config.CHARACTER_DB_PATH  # Use same DB as characters
        self.prizes: List[Prize] = []
        self.prizes_by_rarity: Dict[int, List[Prize]] = {1: [], 2: [], 3: []}
        self.special_prizes: Dict[str, List[Prize]] = (
            {}
        )  # Character -> [special prizes]
        self._create_tables()
        self._load_prizes()

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
            cursor.execute(self.CREATE_TABLE_INVENTORY)
            cursor.execute(self.CREATE_TABLE_ROLL_HISTORY)
            conn.commit()
            logger.info("Gacha tables created/verified successfully")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
        finally:
            conn.close()

    def _load_prizes(self) -> None:
        """Load prizes from CSV file."""
        try:
            with open(config.PRIZES_FILE, "r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    prize = Prize(
                        name=row["Name"].strip('"'),
                        description=row["Description"].strip('"'),
                        rareness=int(row["Rareness"]),
                        special_character=row.get("Special_Character", "").strip()
                        or None,
                    )

                    self.prizes.append(prize)
                    self.prizes_by_rarity[prize.rareness].append(prize)

                    # If it's a special item, add to character mapping
                    if prize.special_character:
                        if prize.special_character not in self.special_prizes:
                            self.special_prizes[prize.special_character] = []
                        self.special_prizes[prize.special_character].append(prize)

            logger.info(f"Loaded {len(self.prizes)} prizes from CSV")
            for rarity, prizes in self.prizes_by_rarity.items():
                logger.info(f"Rarity {rarity}: {len(prizes)} items")

        except Exception as e:
            logger.error(f"Error loading prizes: {e}")

    def _get_random_prize_by_rarity(self, rarity: int) -> Optional[Prize]:
        """Get a random prize of specified rarity."""
        if rarity not in self.prizes_by_rarity or not self.prizes_by_rarity[rarity]:
            return None
        return random.choice(self.prizes_by_rarity[rarity])

    def _get_weighted_random_prize(self) -> Prize:
        """Get a random prize based on rarity weights."""
        # Create weighted list
        weighted_rarities = []
        for rarity, weight in self.RARITY_WEIGHTS.items():
            weighted_rarities.extend([rarity] * weight)

        # Select random rarity
        selected_rarity = random.choice(weighted_rarities)
        return self._get_random_prize_by_rarity(selected_rarity)

    def _apply_special_character_bonus(
        self, prize: Prize, character_name: str
    ) -> Prize:
        """Apply special character bonus if applicable."""
        if (
            prize.rareness == 3
            and character_name in self.special_prizes
            and random.random() < self.SPECIAL_ITEM_CHANCE
        ):

            # 50% chance to get character-specific item
            special_prize = random.choice(self.special_prizes[character_name])
            logger.info(
                f"Special character bonus applied for {character_name}: {special_prize.name}"
            )
            return special_prize

        return prize

    def single_roll(self, character_name: str = None) -> RollResult:
        """Perform a single roll."""
        prize = self._get_weighted_random_prize()

        if character_name:
            prize = self._apply_special_character_bonus(prize, character_name)

        return RollResult(
            prizes=[prize], cost=self.SINGLE_ROLL_COST, roll_type="single"
        )

    def multi_roll_5(self, character_name: str = None) -> RollResult:
        """Perform a 5-roll with guaranteed rare+ item."""
        prizes = []
        guaranteed_used = False

        # Roll 4 times normally
        for _ in range(4):
            prize = self._get_weighted_random_prize()
            if character_name:
                prize = self._apply_special_character_bonus(prize, character_name)
            prizes.append(prize)

        # Check if we need to guarantee a rare+ item
        has_rare_plus = any(prize.rareness >= 2 for prize in prizes)

        if has_rare_plus:
            # Roll normally for the 5th
            prize = self._get_weighted_random_prize()
            if character_name:
                prize = self._apply_special_character_bonus(prize, character_name)
            prizes.append(prize)
        else:
            # Guarantee rare+ for the 5th roll
            rarity = (
                random.choice([2, 3]) if random.random() < 0.2 else 2
            )  # 20% chance for legendary
            prize = self._get_random_prize_by_rarity(rarity)
            if character_name:
                prize = self._apply_special_character_bonus(prize, character_name)
            prizes.append(prize)
            guaranteed_used = True

        return RollResult(
            prizes=prizes,
            cost=self.MULTI_ROLL_5_COST,
            roll_type="multi5",
            guaranteed_used=guaranteed_used,
        )

    def multi_roll_10(self, character_name: str = None) -> RollResult:
        """Perform a 10-roll with guaranteed legendary item."""
        prizes = []
        guaranteed_used = False

        # Roll 9 times normally
        for _ in range(9):
            prize = self._get_weighted_random_prize()
            if character_name:
                prize = self._apply_special_character_bonus(prize, character_name)
            prizes.append(prize)

        # Check if we need to guarantee a legendary item
        has_legendary = any(prize.rareness == 3 for prize in prizes)

        if has_legendary:
            # Roll normally for the 10th
            prize = self._get_weighted_random_prize()
            if character_name:
                prize = self._apply_special_character_bonus(prize, character_name)
            prizes.append(prize)
        else:
            # Guarantee legendary for the 10th roll
            prize = self._get_random_prize_by_rarity(3)
            if character_name:
                prize = self._apply_special_character_bonus(prize, character_name)
            prizes.append(prize)
            guaranteed_used = True

        return RollResult(
            prizes=prizes,
            cost=self.MULTI_ROLL_10_COST,
            roll_type="multi10",
            guaranteed_used=guaranteed_used,
        )

    def add_items_to_inventory(self, discord_id: str, prizes: List[Prize]) -> bool:
        """Add items to user's inventory."""
        conn = self._create_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()

            for prize in prizes:
                # Check if item already exists in inventory
                cursor.execute(
                    """
                    SELECT quantity FROM user_inventory 
                    WHERE discord_id = ? AND item_name = ?
                    """,
                    (discord_id, prize.name),
                )

                result = cursor.fetchone()

                if result:
                    # Update existing item quantity
                    new_quantity = result[0] + 1
                    cursor.execute(
                        """
                        UPDATE user_inventory 
                        SET quantity = ?, obtained_date = CURRENT_TIMESTAMP
                        WHERE discord_id = ? AND item_name = ?
                        """,
                        (new_quantity, discord_id, prize.name),
                    )
                else:
                    # Add new item
                    cursor.execute(
                        """
                        INSERT INTO user_inventory (discord_id, item_name, quantity)
                        VALUES (?, ?, 1)
                        """,
                        (discord_id, prize.name),
                    )

            conn.commit()
            logger.info(f"Added {len(prizes)} items to {discord_id}'s inventory")
            return True

        except Exception as e:
            logger.error(f"Error adding items to inventory: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def record_roll_history(self, discord_id: str, roll_result: RollResult) -> bool:
        """Record roll in history."""
        conn = self._create_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()

            # Create items list string
            items_str = ", ".join([prize.name for prize in roll_result.prizes])

            cursor.execute(
                """
                INSERT INTO roll_history (discord_id, roll_type, cost, items_obtained)
                VALUES (?, ?, ?, ?)
                """,
                (discord_id, roll_result.roll_type, roll_result.cost, items_str),
            )

            conn.commit()
            logger.info(f"Recorded roll history for {discord_id}")
            return True

        except Exception as e:
            logger.error(f"Error recording roll history: {e}")
            return False
        finally:
            conn.close()

    def get_user_inventory(self, discord_id: str) -> List[Tuple]:
        """Get user's inventory."""
        conn = self._create_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT item_name, quantity, obtained_date
                FROM user_inventory 
                WHERE discord_id = ?
                ORDER BY obtained_date DESC
                """,
                (discord_id,),
            )
            return cursor.fetchall()

        except Exception as e:
            logger.error(f"Error getting user inventory: {e}")
            return []
        finally:
            conn.close()

    def get_roll_history(self, discord_id: str, limit: int = 10) -> List[Tuple]:
        """Get user's roll history."""
        conn = self._create_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT roll_type, cost, items_obtained, timestamp
                FROM roll_history 
                WHERE discord_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (discord_id, limit),
            )
            return cursor.fetchall()

        except Exception as e:
            logger.error(f"Error getting roll history: {e}")
            return []
        finally:
            conn.close()

    def get_prize_info(self, item_name: str) -> Optional[Prize]:
        """Get information about a specific prize."""
        for prize in self.prizes:
            if prize.name.lower() == item_name.lower():
                return prize
        return None

    def get_prizes_by_rarity(self, rarity: int) -> List[Prize]:
        """Get all prizes of a specific rarity."""
        return self.prizes_by_rarity.get(rarity, [])

    def get_special_items_for_character(self, character_name: str) -> List[Prize]:
        """Get special items for a specific character."""
        return self.special_prizes.get(character_name, [])
