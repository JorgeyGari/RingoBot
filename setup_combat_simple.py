#!/usr/bin/env python3
"""
Simple script to populate initial combat data without Discord dependencies.
"""

import sys
import os
import sqlite3
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

# Import config
from utils.config import config


def create_connection():
    """Create database connection."""
    try:
        conn = sqlite3.connect(config.CHARACTER_DB_PATH, timeout=10.0)
        conn.execute("PRAGMA busy_timeout=10000")
        return conn
    except Exception as e:
        logger.error(f"Error creating connection: {e}")
        return None


def create_tables():
    """Create combat tables if they don't exist."""
    conn = create_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        # Combat stats table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS combat_stats (
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
        )

        # Enemies table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS enemies (
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
        )

        # Techniques table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS techniques (
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
        )

        # Equipment table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS equipment (
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
        )

        conn.commit()
        logger.info("Combat tables created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        return False
    finally:
        conn.close()


def populate_techniques():
    """Add initial techniques."""
    conn = create_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        techniques = [
            (
                "Golpe Fuerte",
                "Un ataque poderoso que causa daño extra",
                "fuerza",
                "damage",
                5,
                1,
                "enemy",
                None,
                None,
            ),
            (
                "Defensa",
                "Aumenta temporalmente la defensa",
                "aguante",
                "buff",
                3,
                2,
                "self",
                None,
                None,
            ),
            (
                "Esquivar",
                "Aumenta la agilidad temporalmente",
                "agilidad",
                "buff",
                2,
                1,
                "self",
                None,
                None,
            ),
            (
                "Intimidar",
                "Intenta aterrorizar al enemigo",
                "encanto",
                "status",
                0,
                3,
                "enemy",
                "terror",
                None,
            ),
            (
                "Curación",
                "Restaura puntos de vida",
                "conocimiento",
                "heal",
                15,
                2,
                "self",
                None,
                None,
            ),
            (
                "Ataque Venenoso",
                "Ataque que puede causar náuseas",
                "agilidad",
                "status",
                2,
                2,
                "enemy",
                "nauseas",
                None,
            ),
            (
                "Recuerdo Doloroso",
                "Causa nostalgia al enemigo",
                "encanto",
                "status",
                0,
                4,
                "enemy",
                "nostalgia",
                None,
            ),
        ]

        for technique in techniques:
            cursor.execute(
                """
                INSERT OR IGNORE INTO techniques 
                (name, description, associated_stat, effect_type, effect_value, cost, target, status_effect, character_specific)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                technique,
            )

        conn.commit()
        logger.info("Initial techniques populated")
        return True
    except Exception as e:
        logger.error(f"Error populating techniques: {e}")
        return False
    finally:
        conn.close()


def populate_equipment():
    """Add initial equipment."""
    conn = create_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        equipment_items = [
            # Weapons (fuerza bonus)
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
            # Armor (aguante bonus)
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
            # Special items
            ("Corona dorada", "armor", 0, 0, 0, 3, 0, 20, "Símbolo de poder y riqueza"),
        ]

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
        return True
    except Exception as e:
        logger.error(f"Error populating equipment: {e}")
        return False
    finally:
        conn.close()


def populate_enemies():
    """Add demo enemies."""
    conn = create_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        enemies = [
            {
                "name": "Slime Débil",
                "description": "Un pequeño slime gelatinoso. Perfecto para entrenar.",
                "max_hp": 30,
                "fuerza": 1,
                "aguante": 0,
                "agilidad": 0,
                "encanto": 0,
                "conocimiento": 0,
                "techniques": [1, 2],
            },
            {
                "name": "Lobo Salvaje",
                "description": "Un lobo feroz con colmillos afilados. Rápido y peligroso.",
                "max_hp": 50,
                "fuerza": 2,
                "aguante": 1,
                "agilidad": 3,
                "encanto": 0,
                "conocimiento": 1,
                "techniques": [1, 6],
            },
            {
                "name": "Esqueleto Guerrero",
                "description": "Los restos de un antiguo guerrero, animados por magia oscura.",
                "max_hp": 70,
                "fuerza": 3,
                "aguante": 2,
                "agilidad": 1,
                "encanto": 0,
                "conocimiento": 0,
                "techniques": [1, 4],
            },
            {
                "name": "Dragón Joven",
                "description": "Un dragón juvenil con escamas doradas. Su aliento es ardiente.",
                "max_hp": 120,
                "fuerza": 4,
                "aguante": 3,
                "agilidad": 2,
                "encanto": 2,
                "conocimiento": 3,
                "techniques": [1, 4, 7],
            },
            {
                "name": "Golem de Piedra",
                "description": "Una construcción masiva de piedra y magia. Lento pero resistente.",
                "max_hp": 100,
                "fuerza": 5,
                "aguante": 4,
                "agilidad": -1,
                "encanto": 0,
                "conocimiento": 0,
                "techniques": [1, 2],
            },
        ]

        print("Agregando enemigos de demostración...")
        for enemy_data in enemies:
            techniques_json = json.dumps(enemy_data["techniques"])

            cursor.execute(
                """
                INSERT INTO enemies 
                (name, description, max_hp, fuerza_modifier, aguante_modifier, agilidad_modifier,
                 encanto_modifier, conocimiento_modifier, techniques, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    enemy_data["name"],
                    enemy_data["description"],
                    enemy_data["max_hp"],
                    enemy_data["fuerza"],
                    enemy_data["aguante"],
                    enemy_data["agilidad"],
                    enemy_data["encanto"],
                    enemy_data["conocimiento"],
                    techniques_json,
                    "system",
                ),
            )

            print(f"✅ Creado: {enemy_data['name']}")

        conn.commit()
        logger.info("Demo enemies populated")
        return True
    except Exception as e:
        logger.error(f"Error populating enemies: {e}")
        return False
    finally:
        conn.close()


def list_data():
    """List created data."""
    conn = create_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor()

        print("\n=== ENEMIGOS DISPONIBLES ===")
        cursor.execute(
            "SELECT id, name, description, max_hp FROM enemies ORDER BY name"
        )
        enemies = cursor.fetchall()
        for enemy_id, name, description, max_hp in enemies:
            print(f"ID {enemy_id}: {name} ({max_hp} HP)")
            print(f"  {description}")

        print("\n=== TÉCNICAS DISPONIBLES ===")
        cursor.execute(
            "SELECT id, name, description, associated_stat FROM techniques ORDER BY id"
        )
        techniques = cursor.fetchall()
        for tech_id, name, description, stat in techniques:
            print(f"ID {tech_id}: {name} (basada en {stat})")
            print(f"  {description}")

        print("\n=== EQUIPAMIENTO DISPONIBLE ===")
        cursor.execute(
            "SELECT name, equipment_type, fuerza_bonus, aguante_bonus, description FROM equipment ORDER BY equipment_type, name"
        )
        equipment = cursor.fetchall()
        for name, eq_type, fuerza, aguante, desc in equipment:
            bonus_text = []
            if fuerza > 0:
                bonus_text.append(f"+{fuerza} Fuerza")
            if aguante > 0:
                bonus_text.append(f"+{aguante} Aguante")
            bonus_str = ", ".join(bonus_text) if bonus_text else "Sin bonificaciones"
            print(f"{name} ({eq_type}): {bonus_str}")
            print(f"  {desc}")

    except Exception as e:
        logger.error(f"Error listing data: {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    print("🔧 Configurando sistema de combate RPG...")
    print("=" * 50)

    success = True
    success &= create_tables()
    success &= populate_techniques()
    success &= populate_equipment()
    success &= populate_enemies()

    if success:
        list_data()
        print("\n" + "=" * 50)
        print("✅ ¡Sistema de combate configurado correctamente!")
        print("\nComandos disponibles para usar en Discord:")
        print("- /admin crear_enemigo - Crear nuevos enemigos")
        print("- /admin listar_enemigos - Ver todos los enemigos")
        print("- /combate iniciar <enemy_id> <@usuarios> - Iniciar combate")
        print("- /stats ver [@usuario] - Ver estadísticas de combate")
        print("- /stats modificar <@usuario> <stat> <valor> - Modificar stats (admin)")
    else:
        print("❌ Error configurando el sistema de combate")
        sys.exit(1)
