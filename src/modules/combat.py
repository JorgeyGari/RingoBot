"""
Combat module for RPG turn-based combat system.
Handles combat mechanics, enemy management, techniques, and equipment.
"""

import sqlite3
import logging
import json
import random
import asyncio
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

import discord
from discord.ext import commands

from utils.config import config

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Types of actions available in combat."""

    ATTACK = "attack"
    TECHNIQUE = "technique"


class StatusEffect(Enum):
    """Status effects that can be applied in combat."""

    TERROR = "terror"  # 1/5 chance to skip turn
    NAUSEAS = "nauseas"  # Lose 1 HP every 2 turns
    NOSTALGIA = "nostalgia"  # Cannot use techniques


@dataclass
class CombatStats:
    """Character combat statistics."""

    discord_id: str
    fuerza: int = 0
    aguante: int = 0
    agilidad: int = 0
    encanto: int = 0
    conocimiento: int = 0
    max_hp: int = 50
    current_hp: int = 50
    equipped_weapon: Optional[str] = None
    equipped_armor: Optional[str] = None

    def get_total_stat(
        self, stat_name: str, equipment_bonuses: Dict[str, int] = None
    ) -> int:
        """Get total stat including equipment bonuses."""
        base_stat = getattr(self, stat_name, 0)
        if equipment_bonuses and stat_name in equipment_bonuses:
            return base_stat + equipment_bonuses[stat_name]
        return base_stat


@dataclass
class Enemy:
    """Enemy data structure."""

    id: int
    name: str
    description: str
    max_hp: int
    current_hp: int
    fuerza_modifier: int = 0
    aguante_modifier: int = 0
    agilidad_modifier: int = 0
    encanto_modifier: int = 0
    conocimiento_modifier: int = 0
    techniques: List[str] = field(default_factory=list)
    special_abilities: List[str] = field(default_factory=list)


@dataclass
class Technique:
    """Technique data structure."""

    id: int
    name: str
    description: str
    associated_stat: str
    effect_type: str  # "damage", "heal", "status", "buff", "debuff"
    effect_value: int
    cost: int  # Turn cooldown
    target: str  # "self", "enemy", "all_allies"
    status_effect: Optional[str] = None
    character_specific: Optional[str] = None  # Discord ID if character-specific


@dataclass
class Equipment:
    """Equipment data structure."""

    name: str
    equipment_type: str  # "weapon" or "armor"
    fuerza_bonus: int = 0
    aguante_bonus: int = 0
    agilidad_bonus: int = 0
    encanto_bonus: int = 0
    conocimiento_bonus: int = 0
    hp_bonus: int = 0
    description: str = ""


@dataclass
class CombatParticipant:
    """A participant in combat."""

    discord_id: str
    character_name: str
    stats: CombatStats
    status_effects: Dict[StatusEffect, int] = field(
        default_factory=dict
    )  # Effect -> turns remaining
    technique_cooldowns: Dict[int, int] = field(
        default_factory=dict
    )  # Technique ID -> turns remaining
    selected_action: Optional[Dict[str, Any]] = None
    is_alive: bool = True


@dataclass
class CombatSession:
    """Active combat session."""

    channel_id: int
    enemy: Enemy
    participants: List[CombatParticipant]
    turn_phase: str = "player"  # "player" or "enemy"
    message_id: Optional[int] = None
    started_at: datetime = field(default_factory=datetime.now)


class CombatModule:
    """Handles RPG combat system functionality."""

    # Database table creation queries
    CREATE_TABLE_COMBAT_STATS = """CREATE TABLE IF NOT EXISTS combat_stats (
        discord_id TEXT PRIMARY KEY,
        fuerza_modifier INTEGER DEFAULT 0,
        aguante_modifier INTEGER DEFAULT 0,
        agilidad_modifier INTEGER DEFAULT 0,
        encanto_modifier INTEGER DEFAULT 0,
        conocimiento_modifier INTEGER DEFAULT 0,
        max_hp INTEGER DEFAULT 50,
        equipped_weapon TEXT,
        equipped_armor TEXT,
        FOREIGN KEY (discord_id) REFERENCES characters (discord_id)
    );"""

    CREATE_TABLE_ENEMIES = """CREATE TABLE IF NOT EXISTS enemies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        max_hp INTEGER NOT NULL,
        fuerza_modifier INTEGER DEFAULT 0,
        aguante_modifier INTEGER DEFAULT 0,
        agilidad_modifier INTEGER DEFAULT 0,
        encanto_modifier INTEGER DEFAULT 0,
        conocimiento_modifier INTEGER DEFAULT 0,
        techniques TEXT, -- JSON array of technique IDs
        special_abilities TEXT, -- JSON array of special abilities
        created_by TEXT, -- Discord ID of admin who created it
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );"""

    CREATE_TABLE_TECHNIQUES = """CREATE TABLE IF NOT EXISTS techniques (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT NOT NULL,
        associated_stat TEXT NOT NULL, -- fuerza, aguante, agilidad, encanto, conocimiento
        effect_type TEXT NOT NULL, -- damage, heal, status, buff, debuff
        effect_value INTEGER NOT NULL,
        cost INTEGER DEFAULT 0, -- Turn cooldown
        target TEXT DEFAULT 'enemy', -- self, enemy, all_allies
        status_effect TEXT, -- terror, nauseas, nostalgia
        character_specific TEXT, -- Discord ID if character-specific, NULL for common
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );"""

    CREATE_TABLE_EQUIPMENT = """CREATE TABLE IF NOT EXISTS equipment (
        name TEXT PRIMARY KEY,
        equipment_type TEXT NOT NULL, -- weapon, armor
        fuerza_bonus INTEGER DEFAULT 0,
        aguante_bonus INTEGER DEFAULT 0,
        agilidad_bonus INTEGER DEFAULT 0,
        encanto_bonus INTEGER DEFAULT 0,
        conocimiento_bonus INTEGER DEFAULT 0,
        hp_bonus INTEGER DEFAULT 0,
        description TEXT DEFAULT ''
    );"""

    def __init__(self):
        """Initialize the combat module."""
        self.db_path = config.CHARACTER_DB_PATH
        self.active_combats: Dict[int, CombatSession] = (
            {}
        )  # Channel ID -> Combat Session
        self._create_tables()
        self._populate_initial_data()

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
            cursor.execute(self.CREATE_TABLE_COMBAT_STATS)
            cursor.execute(self.CREATE_TABLE_ENEMIES)
            cursor.execute(self.CREATE_TABLE_TECHNIQUES)
            cursor.execute(self.CREATE_TABLE_EQUIPMENT)
            conn.commit()
            logger.info("Combat tables created/verified successfully")
        except Exception as e:
            logger.error(f"Error creating combat tables: {e}")
        finally:
            conn.close()

    def _populate_initial_data(self) -> None:
        """Populate initial techniques and equipment data."""
        self._populate_initial_techniques()
        self._populate_initial_equipment()

    def _populate_initial_techniques(self) -> None:
        """Load techniques from CSV file."""
        import csv
        import os

        techniques_file = os.path.join("data", "techniques.csv")

        if not os.path.exists(techniques_file):
            logger.warning(
                f"Techniques file {techniques_file} not found, skipping technique population"
            )
            return

        conn = self._create_connection()
        if not conn:
            return

        try:
            cursor = conn.cursor()

            with open(techniques_file, "r", encoding="utf-8") as file:
                csv_reader = csv.DictReader(file)

                for row in csv_reader:
                    # Convert empty strings to None for optional fields
                    status_effect = (
                        row["status_effect"] if row["status_effect"].strip() else None
                    )
                    character_specific = (
                        row["character_specific"]
                        if row["character_specific"].strip()
                        else None
                    )

                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO techniques 
                        (name, description, associated_stat, effect_type, effect_value, cost, target, status_effect, character_specific)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            row["name"],
                            row["description"],
                            row["associated_stat"],
                            row["effect_type"],
                            int(row["effect_value"]),
                            int(row["cost"]),
                            row["target"],
                            status_effect,
                            character_specific,
                        ),
                    )

            conn.commit()
            logger.info("Techniques loaded from CSV file")
        except Exception as e:
            logger.error(f"Error loading techniques from CSV: {e}")
        finally:
            conn.close()

    def _populate_initial_equipment(self) -> None:
        """Parse prizes.csv and populate equipment data."""
        conn = self._create_connection()
        if not conn:
            return

        try:
            # Parse equipment from existing prizes.csv
            equipment_items = [
                # Weapons (ATQ = fuerza bonus)
                (
                    "Llave inglesa",
                    "weapon",
                    1,
                    0,
                    0,
                    0,
                    0,
                    0,
                    "Herramienta básica de mecánico",
                ),
                (
                    "Bate de béisbol",
                    "weapon",
                    2,
                    0,
                    0,
                    0,
                    0,
                    0,
                    "El arma idónea en un apocalipsis zombi",
                ),
                (
                    "Espada legendaria",
                    "weapon",
                    10,
                    0,
                    0,
                    0,
                    0,
                    0,
                    "Una espada de poder incalculable",
                ),
                (
                    "Grimorio ancestral",
                    "weapon",
                    0,
                    0,
                    0,
                    0,
                    8,
                    0,
                    "Libro de hechizos antiguos",
                ),
                # Armor (DEF = aguante bonus)
                (
                    "Armadura ligera",
                    "armor",
                    0,
                    3,
                    0,
                    0,
                    0,
                    0,
                    "Protección básica contra ataques",
                ),
                (
                    "Colgante místico",
                    "armor",
                    0,
                    5,
                    0,
                    2,
                    2,
                    0,
                    "La mejor armadura para Hikaru",
                ),
                # Items that give HP bonuses
                (
                    "Corona dorada",
                    "armor",
                    0,
                    0,
                    0,
                    3,
                    0,
                    20,
                    "Símbolo de poder y riqueza",
                ),
            ]

            cursor = conn.cursor()
            for equipment in equipment_items:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO equipment 
                    (name, equipment_type, fuerza_bonus, aguante_bonus, agilidad_bonus, encanto_bonus, conocimiento_bonus, hp_bonus, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    equipment,
                )
            conn.commit()
            logger.info("Initial equipment populated")
        except Exception as e:
            logger.error(f"Error populating initial equipment: {e}")
        finally:
            conn.close()

    # Character combat stats management
    def get_character_combat_stats(self, discord_id: str) -> Optional[CombatStats]:
        """Get character's combat stats."""
        conn = self._create_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT discord_id, fuerza_modifier, aguante_modifier, agilidad_modifier, 
                       encanto_modifier, conocimiento_modifier, max_hp, equipped_weapon, equipped_armor
                FROM combat_stats WHERE discord_id = ?
            """,
                (discord_id,),
            )

            result = cursor.fetchone()
            if result:
                return CombatStats(
                    discord_id=result[0],
                    fuerza=result[1],
                    aguante=result[2],
                    agilidad=result[3],
                    encanto=result[4],
                    conocimiento=result[5],
                    max_hp=result[6],
                    current_hp=result[6],  # Start at max HP
                    equipped_weapon=result[7],
                    equipped_armor=result[8],
                )
            else:
                # Create default stats for new character
                return self._create_default_combat_stats(discord_id)
        except Exception as e:
            logger.error(f"Error getting combat stats: {e}")
            return None
        finally:
            conn.close()

    def _create_default_combat_stats(self, discord_id: str) -> CombatStats:
        """Create default combat stats for a character."""
        conn = self._create_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR IGNORE INTO combat_stats (discord_id) VALUES (?)
            """,
                (discord_id,),
            )
            conn.commit()
            logger.info(f"Created default combat stats for {discord_id}")

            return CombatStats(
                discord_id=discord_id,
                fuerza=0,
                aguante=0,
                agilidad=0,
                encanto=0,
                conocimiento=0,
                max_hp=50,
                current_hp=50,
            )
        except Exception as e:
            logger.error(f"Error creating default combat stats: {e}")
            return None
        finally:
            conn.close()

    def update_combat_stats(self, discord_id: str, **stats) -> bool:
        """Update character's combat stats."""
        conn = self._create_connection()
        if not conn:
            return False

        try:
            # Build dynamic query
            valid_stats = [
                "fuerza_modifier",
                "aguante_modifier",
                "agilidad_modifier",
                "encanto_modifier",
                "conocimiento_modifier",
                "max_hp",
                "equipped_weapon",
                "equipped_armor",
            ]

            updates = []
            params = []

            for stat, value in stats.items():
                if stat in valid_stats:
                    updates.append(f"{stat} = ?")
                    params.append(value)

            if not updates:
                return True

            params.append(discord_id)
            query = f"UPDATE combat_stats SET {', '.join(updates)} WHERE discord_id = ?"

            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()

            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating combat stats: {e}")
            return False
        finally:
            conn.close()

    # Equipment management
    def get_equipment(self, equipment_name: str) -> Optional[Equipment]:
        """Get equipment details."""
        conn = self._create_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT name, equipment_type, fuerza_bonus, aguante_bonus, agilidad_bonus,
                       encanto_bonus, conocimiento_bonus, hp_bonus, description
                FROM equipment WHERE name = ?
            """,
                (equipment_name,),
            )

            result = cursor.fetchone()
            if result:
                return Equipment(
                    name=result[0],
                    equipment_type=result[1],
                    fuerza_bonus=result[2],
                    aguante_bonus=result[3],
                    agilidad_bonus=result[4],
                    encanto_bonus=result[5],
                    conocimiento_bonus=result[6],
                    hp_bonus=result[7],
                    description=result[8],
                )
            return None
        except Exception as e:
            logger.error(f"Error getting equipment: {e}")
            return None
        finally:
            conn.close()

    def get_equipment_bonuses(self, discord_id: str) -> Dict[str, int]:
        """Get total equipment bonuses for a character."""
        stats = self.get_character_combat_stats(discord_id)
        if not stats:
            return {}

        bonuses = {
            "fuerza": 0,
            "aguante": 0,
            "agilidad": 0,
            "encanto": 0,
            "conocimiento": 0,
            "max_hp": 0,
        }

        if stats.equipped_weapon:
            weapon = self.get_equipment(stats.equipped_weapon)
            if weapon:
                bonuses["fuerza"] += weapon.fuerza_bonus
                bonuses["aguante"] += weapon.aguante_bonus
                bonuses["agilidad"] += weapon.agilidad_bonus
                bonuses["encanto"] += weapon.encanto_bonus
                bonuses["conocimiento"] += weapon.conocimiento_bonus
                bonuses["max_hp"] += weapon.hp_bonus

        if stats.equipped_armor:
            armor = self.get_equipment(stats.equipped_armor)
            if armor:
                bonuses["fuerza"] += armor.fuerza_bonus
                bonuses["aguante"] += armor.aguante_bonus
                bonuses["agilidad"] += armor.agilidad_bonus
                bonuses["encanto"] += armor.encanto_bonus
                bonuses["conocimiento"] += armor.conocimiento_bonus
                bonuses["max_hp"] += armor.hp_bonus

        return bonuses

    # Enemy management
    def create_enemy(
        self,
        name: str,
        description: str,
        max_hp: int,
        fuerza: int = 0,
        aguante: int = 0,
        agilidad: int = 0,
        encanto: int = 0,
        conocimiento: int = 0,
        techniques: List[int] = None,
        created_by: str = "",
    ) -> Optional[int]:
        """Create a new enemy."""
        conn = self._create_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            techniques_json = json.dumps(techniques or [])

            cursor.execute(
                """
                INSERT INTO enemies 
                (name, description, max_hp, fuerza_modifier, aguante_modifier, agilidad_modifier,
                 encanto_modifier, conocimiento_modifier, techniques, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    name,
                    description,
                    max_hp,
                    fuerza,
                    aguante,
                    agilidad,
                    encanto,
                    conocimiento,
                    techniques_json,
                    created_by,
                ),
            )

            conn.commit()
            enemy_id = cursor.lastrowid
            logger.info(f"Enemy '{name}' created with ID {enemy_id}")
            return enemy_id
        except Exception as e:
            logger.error(f"Error creating enemy: {e}")
            return None
        finally:
            conn.close()

    def get_enemy(self, enemy_id: int) -> Optional[Enemy]:
        """Get enemy by ID."""
        conn = self._create_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, description, max_hp, fuerza_modifier, aguante_modifier,
                       agilidad_modifier, encanto_modifier, conocimiento_modifier, techniques, special_abilities
                FROM enemies WHERE id = ?
            """,
                (enemy_id,),
            )

            result = cursor.fetchone()
            if result:
                techniques = json.loads(result[9]) if result[9] else []
                special_abilities = json.loads(result[10]) if result[10] else []

                return Enemy(
                    id=result[0],
                    name=result[1],
                    description=result[2],
                    max_hp=result[3],
                    current_hp=result[3],  # Start at max HP
                    fuerza_modifier=result[4],
                    aguante_modifier=result[5],
                    agilidad_modifier=result[6],
                    encanto_modifier=result[7],
                    conocimiento_modifier=result[8],
                    techniques=techniques,
                    special_abilities=special_abilities,
                )
            return None
        except Exception as e:
            logger.error(f"Error getting enemy: {e}")
            return None
        finally:
            conn.close()

    # Technique management
    def get_available_techniques(self, discord_id: str) -> List[Technique]:
        """Get techniques available to a character."""
        conn = self._create_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, description, associated_stat, effect_type, effect_value,
                       cost, target, status_effect, character_specific
                FROM techniques 
                WHERE character_specific IS NULL OR character_specific = ?
            """,
                (discord_id,),
            )

            techniques = []
            for row in cursor.fetchall():
                techniques.append(
                    Technique(
                        id=row[0],
                        name=row[1],
                        description=row[2],
                        associated_stat=row[3],
                        effect_type=row[4],
                        effect_value=row[5],
                        cost=row[6],
                        target=row[7],
                        status_effect=row[8],
                        character_specific=row[9],
                    )
                )

            return techniques
        except Exception as e:
            logger.error(f"Error getting available techniques: {e}")
            return []
        finally:
            conn.close()

    def get_technique(self, technique_id: int) -> Optional[Technique]:
        """Get technique by ID."""
        conn = self._create_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, description, associated_stat, effect_type, effect_value,
                       cost, target, status_effect, character_specific
                FROM techniques WHERE id = ?
            """,
                (technique_id,),
            )

            result = cursor.fetchone()
            if result:
                return Technique(
                    id=result[0],
                    name=result[1],
                    description=result[2],
                    associated_stat=result[3],
                    effect_type=result[4],
                    effect_value=result[5],
                    cost=result[6],
                    target=result[7],
                    status_effect=result[8],
                    character_specific=result[9],
                )
            return None
        except Exception as e:
            logger.error(f"Error getting technique: {e}")
            return None
        finally:
            conn.close()

    # Combat mechanics
    def start_combat(
        self,
        channel_id: int,
        enemy_id: int,
        participant_ids: List[str],
        character_names: Dict[str, str],
    ) -> bool:
        """Start a new combat session."""
        if channel_id in self.active_combats:
            logger.warning(f"Combat already active in channel {channel_id}")
            return False

        enemy = self.get_enemy(enemy_id)
        if not enemy:
            logger.error(f"Enemy {enemy_id} not found")
            return False

        participants = []
        for discord_id in participant_ids:
            stats = self.get_character_combat_stats(discord_id)
            if stats:
                # Apply equipment bonuses to max HP
                equipment_bonuses = self.get_equipment_bonuses(discord_id)
                max_hp_with_equipment = stats.max_hp + equipment_bonuses.get(
                    "max_hp", 0
                )
                stats.max_hp = max_hp_with_equipment
                stats.current_hp = max_hp_with_equipment

                participant = CombatParticipant(
                    discord_id=discord_id,
                    character_name=character_names.get(
                        discord_id, f"Player {discord_id}"
                    ),
                    stats=stats,
                )
                participants.append(participant)

        if not participants:
            logger.error("No valid participants for combat")
            return False

        # Sort participants by agilidad (initiative order)
        participants.sort(key=lambda p: self._get_total_agilidad(p), reverse=True)

        combat_session = CombatSession(
            channel_id=channel_id, enemy=enemy, participants=participants
        )

        self.active_combats[channel_id] = combat_session
        logger.info(f"Combat started in channel {channel_id} with enemy {enemy.name}")
        return True

    def end_combat(self, channel_id: int) -> bool:
        """End combat session."""
        if channel_id not in self.active_combats:
            return False

        del self.active_combats[channel_id]
        logger.info(f"Combat ended in channel {channel_id}")
        return True

    def get_combat_session(self, channel_id: int) -> Optional[CombatSession]:
        """Get active combat session."""
        return self.active_combats.get(channel_id)

    def set_player_action(
        self, channel_id: int, discord_id: str, action: Dict[str, Any]
    ) -> bool:
        """Set a player's action for the current turn."""
        combat = self.get_combat_session(channel_id)
        if not combat or combat.turn_phase != "player":
            return False

        participant = self._get_participant(combat, discord_id)
        if not participant or not participant.is_alive:
            return False

        participant.selected_action = action
        logger.info(f"Player {discord_id} selected action: {action}")
        return True

    def all_players_ready(self, channel_id: int) -> bool:
        """Check if all alive players have selected their actions."""
        combat = self.get_combat_session(channel_id)
        if not combat:
            return False

        for participant in combat.participants:
            if participant.is_alive and participant.selected_action is None:
                return False
        return True

    def process_player_turn(self, channel_id: int) -> List[str]:
        """Process all player actions for the current turn."""
        combat = self.get_combat_session(channel_id)
        if not combat or combat.turn_phase != "player":
            return []

        results = []

        # Reduce cooldowns for all participants at the start of the turn
        for participant in combat.participants:
            if participant.technique_cooldowns:
                # Reduce all cooldowns by 1, remove those that reach 0
                cooldowns_to_remove = []
                for (
                    technique_id,
                    remaining_turns,
                ) in participant.technique_cooldowns.items():
                    if remaining_turns > 0:
                        participant.technique_cooldowns[technique_id] = (
                            remaining_turns - 1
                        )
                        if participant.technique_cooldowns[technique_id] <= 0:
                            cooldowns_to_remove.append(technique_id)

                # Remove expired cooldowns
                for technique_id in cooldowns_to_remove:
                    del participant.technique_cooldowns[technique_id]

        # Process each player's action in agilidad order
        for participant in combat.participants:
            if not participant.is_alive or participant.selected_action is None:
                continue

            # Check status effects
            status_result = self._process_status_effects(participant)
            if status_result:
                results.append(status_result)

            # Skip turn if affected by terror
            if StatusEffect.TERROR in participant.status_effects:
                if random.randint(1, 5) == 1:  # 1/5 chance to skip
                    results.append(
                        f"😰 **{participant.character_name}** está paralizado por el terror y no puede actuar!"
                    )
                    participant.selected_action = None
                    continue

            action = participant.selected_action
            action_result = self._execute_action(
                participant, combat.enemy, action, combat.participants
            )
            if action_result:
                results.append(action_result)

            # Reset action
            participant.selected_action = None

        # Check if enemy is defeated
        if combat.enemy.current_hp <= 0:
            results.append(f"🎉 **{combat.enemy.name}** ha sido derrotado!")
            return results

        # Move to enemy turn
        combat.turn_phase = "enemy"
        return results

    def process_enemy_turn(self, channel_id: int) -> List[str]:
        """Process enemy's turn."""
        combat = self.get_combat_session(channel_id)
        if not combat or combat.turn_phase != "enemy":
            return []

        results = []
        enemy = combat.enemy
        alive_participants = [p for p in combat.participants if p.is_alive]

        if not alive_participants:
            results.append("💀 Todos los participantes han caído en combate.")
            return results

        # Enemy AI: choose action based on HP percentage
        hp_percentage = enemy.current_hp / enemy.max_hp
        action = self._choose_enemy_action(enemy, hp_percentage)

        if action["type"] == "attack":
            # Choose random target
            target = random.choice(alive_participants)
            attack_result = self._enemy_attack(enemy, target)
            results.append(attack_result)
        elif action["type"] == "technique":
            technique_result = self._enemy_use_technique(
                enemy, action["technique_id"], alive_participants
            )
            results.append(technique_result)

        # Check if any players are defeated
        for participant in combat.participants:
            if participant.is_alive and participant.stats.current_hp <= 0:
                participant.is_alive = False
                results.append(
                    f"💀 **{participant.character_name}** ha caído en combate!"
                )

        # Move back to player turn
        combat.turn_phase = "player"
        return results

    def _get_participant(
        self, combat: CombatSession, discord_id: str
    ) -> Optional[CombatParticipant]:
        """Get participant by Discord ID."""
        for participant in combat.participants:
            if participant.discord_id == discord_id:
                return participant
        return None

    def _get_total_agilidad(self, participant: CombatParticipant) -> int:
        """Get participant's total agilidad including equipment."""
        equipment_bonuses = self.get_equipment_bonuses(participant.discord_id)
        return participant.stats.agilidad + equipment_bonuses.get("agilidad", 0)

    def _process_status_effects(self, participant: CombatParticipant) -> Optional[str]:
        """Process status effects and return result message."""
        results = []

        # Process náuseas (lose 1 HP every 2 turns)
        if StatusEffect.NAUSEAS in participant.status_effects:
            participant.status_effects[StatusEffect.NAUSEAS] -= 1
            if participant.status_effects[StatusEffect.NAUSEAS] % 2 == 0:
                participant.stats.current_hp = max(0, participant.stats.current_hp - 1)
                results.append(
                    f"🤢 **{participant.character_name}** pierde 1 HP por náuseas"
                )

            if participant.status_effects[StatusEffect.NAUSEAS] <= 0:
                del participant.status_effects[StatusEffect.NAUSEAS]
                results.append(
                    f"✨ **{participant.character_name}** se recupera de las náuseas"
                )

        # Decrease other status effect durations
        effects_to_remove = []
        for effect, duration in participant.status_effects.items():
            if effect != StatusEffect.NAUSEAS:
                participant.status_effects[effect] = duration - 1
                if participant.status_effects[effect] <= 0:
                    effects_to_remove.append(effect)

        for effect in effects_to_remove:
            del participant.status_effects[effect]
            effect_name = {"terror": "terror", "nostalgia": "nostalgia"}[effect.value]
            results.append(
                f"✨ **{participant.character_name}** se recupera del {effect_name}"
            )

        return " | ".join(results) if results else None

    def _execute_action(
        self,
        participant: CombatParticipant,
        enemy: Enemy,
        action: Dict[str, Any],
        all_participants: List[CombatParticipant],
    ) -> str:
        """Execute a participant's action."""
        if action["type"] == "attack":
            return self._player_attack(participant, enemy)
        elif action["type"] == "technique":
            # Check if can use techniques (nostalgia effect)
            if StatusEffect.NOSTALGIA in participant.status_effects:
                return f"😔 **{participant.character_name}** no puede usar técnicas debido a la nostalgia"

            technique_id = action["technique_id"]

            # Check cooldown
            if (
                technique_id in participant.technique_cooldowns
                and participant.technique_cooldowns[technique_id] > 0
            ):
                return f"⏳ **{participant.character_name}** debe esperar {participant.technique_cooldowns[technique_id]} turnos más para usar esta técnica"

            return self._player_use_technique(
                participant, enemy, technique_id, all_participants
            )

        return f"❓ **{participant.character_name}** intenta hacer algo extraño..."

    def _player_attack(self, participant: CombatParticipant, enemy: Enemy) -> str:
        """Execute player attack."""
        equipment_bonuses = self.get_equipment_bonuses(participant.discord_id)

        # Roll dice: 1d6 + Fuerza
        attack_roll = (
            random.randint(1, 6)
            + participant.stats.fuerza
            + equipment_bonuses.get("fuerza", 0)
        )
        defense_roll = random.randint(1, 6) + enemy.aguante_modifier

        if attack_roll > defense_roll:
            damage = attack_roll - defense_roll
            enemy.current_hp = max(0, enemy.current_hp - damage)
            return f"⚔️ **{participant.character_name}** ataca ({attack_roll}) vs {enemy.name} ({defense_roll}) - ¡{damage} de daño! [{enemy.current_hp}/{enemy.max_hp} HP]"
        else:
            return f"🛡️ **{participant.character_name}** ataca ({attack_roll}) vs {enemy.name} ({defense_roll}) - ¡El ataque no conecta!"

    def _player_use_technique(
        self,
        participant: CombatParticipant,
        enemy: Enemy,
        technique_id: int,
        all_participants: List[CombatParticipant],
    ) -> str:
        """Execute player technique."""
        technique = self.get_technique(technique_id)
        if not technique:
            return f"❓ **{participant.character_name}** intenta usar una técnica desconocida"

        equipment_bonuses = self.get_equipment_bonuses(participant.discord_id)
        associated_stat_value = getattr(
            participant.stats, technique.associated_stat, 0
        ) + equipment_bonuses.get(technique.associated_stat, 0)

        # Set cooldown
        participant.technique_cooldowns[technique_id] = technique.cost

        if technique.effect_type == "damage":
            # Roll dice: 1d6 + associated stat + technique value
            attack_roll = (
                random.randint(1, 6) + associated_stat_value + technique.effect_value
            )
            defense_roll = random.randint(1, 6) + enemy.aguante_modifier

            if attack_roll > defense_roll:
                damage = attack_roll - defense_roll
                enemy.current_hp = max(0, enemy.current_hp - damage)
                result = f"✨ **{participant.character_name}** usa *{technique.name}* ({attack_roll}) vs {enemy.name} ({defense_roll}) - ¡{damage} de daño! [{enemy.current_hp}/{enemy.max_hp} HP]"
            else:
                result = f"✨ **{participant.character_name}** usa *{technique.name}* ({attack_roll}) vs {enemy.name} ({defense_roll}) - ¡Falló!"

        elif technique.effect_type == "heal":
            heal_amount = technique.effect_value
            old_hp = participant.stats.current_hp
            participant.stats.current_hp = min(
                participant.stats.max_hp, participant.stats.current_hp + heal_amount
            )
            actual_heal = participant.stats.current_hp - old_hp
            result = f"💚 **{participant.character_name}** usa *{technique.name}* y recupera {actual_heal} HP [{participant.stats.current_hp}/{participant.stats.max_hp} HP]"

        elif technique.effect_type == "status":
            if (
                technique.status_effect
                and random.randint(1, 6) + associated_stat_value > 3
            ):  # Success check
                status_effect = StatusEffect(technique.status_effect)
                # Status effects last 3-5 turns
                duration = random.randint(3, 5)
                # Apply to enemy (simplified - in a full system, you'd need to track enemy status effects)
                result = f"✨ **{participant.character_name}** usa *{technique.name}* - ¡{enemy.name} sufre {technique.status_effect}!"
            else:
                result = f"✨ **{participant.character_name}** usa *{technique.name}* - ¡Pero no tiene efecto!"

        elif technique.effect_type in ["buff", "debuff"]:
            # Temporary stat modifications (simplified implementation)
            result = f"✨ **{participant.character_name}** usa *{technique.name}* - ¡Se siente más poderoso!"

        else:
            result = f"✨ **{participant.character_name}** usa *{technique.name}*"

        # Apply status effect if applicable
        if technique.status_effect and technique.effect_type == "status":
            # This would need more complex implementation for enemy status tracking
            pass

        return result

    def _choose_enemy_action(
        self, enemy: Enemy, hp_percentage: float
    ) -> Dict[str, Any]:
        """Choose enemy action based on AI logic."""
        # Simple AI: more aggressive when low on health
        if hp_percentage > 0.7:
            # High health: 80% attack, 20% technique
            if random.random() < 0.8:
                return {"type": "attack"}
            else:
                return (
                    {
                        "type": "technique",
                        "technique_id": random.choice(enemy.techniques),
                    }
                    if enemy.techniques
                    else {"type": "attack"}
                )
        elif hp_percentage > 0.3:
            # Medium health: 60% attack, 40% technique
            if random.random() < 0.6:
                return {"type": "attack"}
            else:
                return (
                    {
                        "type": "technique",
                        "technique_id": random.choice(enemy.techniques),
                    }
                    if enemy.techniques
                    else {"type": "attack"}
                )
        else:
            # Low health: 40% attack, 60% technique (more desperate)
            if random.random() < 0.4:
                return {"type": "attack"}
            else:
                return (
                    {
                        "type": "technique",
                        "technique_id": random.choice(enemy.techniques),
                    }
                    if enemy.techniques
                    else {"type": "attack"}
                )

    def _enemy_attack(self, enemy: Enemy, target: CombatParticipant) -> str:
        """Execute enemy attack."""
        equipment_bonuses = self.get_equipment_bonuses(target.discord_id)

        # Roll dice: 1d6 + Fuerza
        attack_roll = random.randint(1, 6) + enemy.fuerza_modifier
        defense_roll = (
            random.randint(1, 6)
            + target.stats.aguante
            + equipment_bonuses.get("aguante", 0)
        )

        if attack_roll > defense_roll:
            damage = attack_roll - defense_roll
            target.stats.current_hp = max(0, target.stats.current_hp - damage)
            return f"👹 **{enemy.name}** ataca a {target.character_name} ({attack_roll}) vs ({defense_roll}) - ¡{damage} de daño! [{target.stats.current_hp}/{target.stats.max_hp} HP]"
        else:
            return f"🛡️ **{enemy.name}** ataca a {target.character_name} ({attack_roll}) vs ({defense_roll}) - ¡{target.character_name} esquiva el ataque!"

    def _enemy_use_technique(
        self, enemy: Enemy, technique_id: int, targets: List[CombatParticipant]
    ) -> str:
        """Execute enemy technique."""
        # Simplified enemy technique usage
        target = random.choice(targets)
        return f"👹 **{enemy.name}** usa una habilidad especial contra {target.character_name}!"

    # Admin commands
    def list_enemies(self) -> List[Tuple]:
        """List all enemies."""
        conn = self._create_connection()
        if not conn:
            return []

        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, description, max_hp FROM enemies ORDER BY name"
            )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error listing enemies: {e}")
            return []
        finally:
            conn.close()

    def delete_enemy(self, enemy_id: int) -> bool:
        """Delete an enemy."""
        conn = self._create_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM enemies WHERE id = ?", (enemy_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting enemy: {e}")
            return False
        finally:
            conn.close()
