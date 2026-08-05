#!/usr/bin/env python3
"""
Script to populate the database with some demo enemies for testing the combat system.
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from modules.combat import CombatModule


def create_demo_enemies():
    """Create some demo enemies for testing."""
    combat_module = CombatModule()

    # Demo enemies with different difficulty levels
    enemies = [
        {
            "name": "Lobo Salvaje",
            "description": "Un lobo hambriento con ojos brillantes y colmillos afilados.",
            "max_hp": 30,
            "fuerza": 2,
            "aguante": 1,
            "agilidad": 3,
            "encanto": 0,
            "conocimiento": 0,
        },
        {
            "name": "Orco Guerrero",
            "description": "Un orco brutal armado con un hacha oxidada y sed de batalla.",
            "max_hp": 50,
            "fuerza": 4,
            "aguante": 3,
            "agilidad": 1,
            "encanto": -1,
            "conocimiento": 0,
        },
        {
            "name": "Esqueleto Arcano",
            "description": "Los restos de un antiguo mago, ahora reanimado con magia oscura.",
            "max_hp": 40,
            "fuerza": 1,
            "aguante": 2,
            "agilidad": 2,
            "encanto": 1,
            "conocimiento": 4,
        },
        {
            "name": "Dragón Joven",
            "description": "Un dragón joven pero feroz, con escamas doradas y aliento de fuego.",
            "max_hp": 100,
            "fuerza": 6,
            "aguante": 5,
            "agilidad": 4,
            "encanto": 3,
            "conocimiento": 3,
        },
        {
            "name": "Goblin Ladrón",
            "description": "Un pequeño goblin ágil y astuto que ataca desde las sombras.",
            "max_hp": 20,
            "fuerza": 1,
            "aguante": 0,
            "agilidad": 4,
            "encanto": 2,
            "conocimiento": 1,
        },
    ]

    created_enemies = []
    for enemy_data in enemies:
        enemy_id = combat_module.create_enemy(
            name=enemy_data["name"],
            description=enemy_data["description"],
            max_hp=enemy_data["max_hp"],
            fuerza=enemy_data["fuerza"],
            aguante=enemy_data["aguante"],
            agilidad=enemy_data["agilidad"],
            encanto=enemy_data["encanto"],
            conocimiento=enemy_data["conocimiento"],
            created_by="system_demo",
        )

        if enemy_id:
            created_enemies.append((enemy_id, enemy_data["name"]))
            print(f"✅ Creado: {enemy_data['name']} (ID: {enemy_id})")
        else:
            print(f"❌ Error al crear: {enemy_data['name']}")

    print(f"\n🎉 Se crearon {len(created_enemies)} enemigos de demostración.")
    print("\nPuedes usar estos IDs para iniciar combates:")
    for enemy_id, name in created_enemies:
        print(f"  ID {enemy_id}: {name}")


if __name__ == "__main__":
    create_demo_enemies()
