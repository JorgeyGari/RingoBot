#!/usr/bin/env python3
"""
Script to populate initial combat data for testing.
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from modules.combat import CombatModule


def populate_demo_enemies():
    """Add some demo enemies to the database."""
    combat_module = CombatModule()

    # Demo enemies with different difficulties
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
            "techniques": [1, 2],  # Simple attack techniques
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
            "techniques": [1, 6],  # Attack and poison
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
            "techniques": [1, 4],  # Attack and intimidate
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
            "techniques": [1, 4, 7],  # Attack, intimidate, nostalgia
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
            "techniques": [1, 2],  # Attack and defense
        },
    ]

    print("Agregando enemigos de demostración...")

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
            techniques=enemy_data["techniques"],
            created_by="system",
        )

        if enemy_id:
            print(f"✅ Creado: {enemy_data['name']} (ID: {enemy_id})")
        else:
            print(f"❌ Error creando: {enemy_data['name']}")

    print("\n¡Enemigos de demostración agregados!")

    # List all enemies
    print("\nEnemigos disponibles:")
    enemies_list = combat_module.list_enemies()
    for enemy_id, name, description, max_hp in enemies_list:
        print(f"ID {enemy_id}: {name} ({max_hp} HP)")


def test_combat_stats():
    """Test combat stats functionality."""
    combat_module = CombatModule()

    # Test creating default stats for a demo user
    demo_user_id = "123456789"
    stats = combat_module.get_character_combat_stats(demo_user_id)

    if stats:
        print(f"\nEstadísticas por defecto creadas para usuario {demo_user_id}:")
        print(f"Fuerza: {stats.fuerza}")
        print(f"Aguante: {stats.aguante}")
        print(f"Agilidad: {stats.agilidad}")
        print(f"Encanto: {stats.encanto}")
        print(f"Conocimiento: {stats.conocimiento}")
        print(f"HP Máximo: {stats.max_hp}")
    else:
        print("❌ Error creando estadísticas de prueba")


def show_techniques():
    """Show available techniques."""
    combat_module = CombatModule()
    techniques = combat_module.get_available_techniques("demo_user")

    print("\nTécnicas disponibles:")
    for technique in techniques:
        print(f"ID {technique.id}: {technique.name}")
        print(f"  Descripción: {technique.description}")
        print(f"  Estadística: {technique.associated_stat}")
        print(f"  Tipo: {technique.effect_type}")
        print(f"  Valor: {technique.effect_value}")
        print(f"  Coste: {technique.cost} turnos")
        print()


def show_equipment():
    """Show available equipment."""
    combat_module = CombatModule()

    print("Equipamiento disponible:")

    # Get some sample equipment
    weapons = [
        "Llave inglesa",
        "Bate de béisbol",
        "Espada legendaria",
        "Grimorio ancestral",
    ]
    armors = ["Armadura ligera", "Colgante místico", "Corona dorada"]

    print("\n🗡️ Armas:")
    for weapon_name in weapons:
        weapon = combat_module.get_equipment(weapon_name)
        if weapon:
            print(
                f"- {weapon.name}: +{weapon.fuerza_bonus} Fuerza, +{weapon.conocimiento_bonus} Conocimiento"
            )
            print(f"  {weapon.description}")

    print("\n🛡️ Armaduras:")
    for armor_name in armors:
        armor = combat_module.get_equipment(armor_name)
        if armor:
            print(
                f"- {armor.name}: +{armor.aguante_bonus} Aguante, +{armor.encanto_bonus} Encanto, +{armor.hp_bonus} HP"
            )
            print(f"  {armor.description}")


if __name__ == "__main__":
    print("🔧 Configurando datos iniciales del sistema de combate...")
    print("=" * 50)

    populate_demo_enemies()
    test_combat_stats()
    show_techniques()
    show_equipment()

    print("\n" + "=" * 50)
    print("✅ ¡Sistema de combate listo para usar!")
    print("\nComandos disponibles:")
    print("- /admin crear_enemigo - Crear nuevos enemigos")
    print("- /admin listar_enemigos - Ver todos los enemigos")
    print("- /combate iniciar <enemy_id> <@usuarios> - Iniciar combate")
    print("- /stats ver [@usuario] - Ver estadísticas de combate")
    print("- /stats modificar <@usuario> <stat> <valor> - Modificar stats (admin)")
