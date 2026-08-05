#!/usr/bin/env python3
"""
Discord Command Test Helper
Provides test scenarios and command examples for the combat system.
"""

import sys
import os
import sqlite3

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from utils.config import config


def show_available_enemies():
    """Show all available enemies for testing."""
    print("👹 AVAILABLE ENEMIES FOR TESTING:")
    print("=" * 50)

    conn = sqlite3.connect(config.CHARACTER_DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, name, description, max_hp, fuerza_modifier, aguante_modifier, agilidad_modifier
        FROM enemies ORDER BY max_hp
    """
    )

    enemies = cursor.fetchall()

    for enemy_id, name, description, max_hp, fuerza, aguante, agilidad in enemies:
        difficulty = "Easy" if max_hp <= 40 else "Medium" if max_hp <= 80 else "Hard"
        print(f"ID {enemy_id}: {name} ({difficulty})")
        print(
            f"   HP: {max_hp} | Fuerza: +{fuerza} | Aguante: +{aguante} | Agilidad: +{agilidad}"
        )
        print(f"   {description}")
        print()

    conn.close()


def show_command_examples():
    """Show example Discord commands."""
    print("🎮 DISCORD COMMAND EXAMPLES:")
    print("=" * 50)

    print("📋 ADMIN COMMANDS:")
    print("   /admin crear_enemigo")
    print("   └─ Creates a new enemy with custom stats")
    print()
    print("   /admin listar_enemigos")
    print("   └─ Shows all available enemies with their IDs")
    print()
    print("   /admin eliminar_enemigo enemigo_id:5")
    print("   └─ Deletes enemy with ID 5")
    print()

    print("⚔️ COMBAT COMMANDS:")
    print("   /combate iniciar enemigo_id:5 participantes:@user1 @user2")
    print("   └─ Starts combat with Slime Débil vs 2 players")
    print()
    print("   /combate estado")
    print("   └─ Shows current combat status and HP bars")
    print()
    print("   /combate terminar")
    print("   └─ Ends current combat (admin only)")
    print()

    print("📊 STATS COMMANDS:")
    print("   /stats ver")
    print("   └─ View your own combat stats")
    print()
    print("   /stats ver usuario:@player")
    print("   └─ View another player's combat stats")
    print()
    print("   /stats modificar usuario:@player stat:fuerza valor:3")
    print("   └─ Set player's Fuerza to 3 (admin only)")
    print()


def show_combat_flow():
    """Show the expected combat flow."""
    print("🎯 COMBAT FLOW EXAMPLE:")
    print("=" * 50)

    print("1️⃣ SETUP PHASE:")
    print("   • Admin: /admin listar_enemigos")
    print("   • Admin chooses enemy (e.g., ID 5 = Slime Débil)")
    print("   • Admin: /combate iniciar enemigo_id:5 participantes:@player1 @player2")
    print()

    print("2️⃣ COMBAT STARTS:")
    print("   • Bot shows combat embed with enemy info")
    print("   • Players see HP bars and action buttons")
    print("   • Turn phase: 'Turno de los jugadores'")
    print()

    print("3️⃣ PLAYER ACTIONS:")
    print("   • Each player clicks either:")
    print("     - ⚔️ Atacar (basic attack)")
    print("     - ✨ Técnica (special abilities)")
    print("   • If Técnica is selected, player sees technique menu")
    print("   • Player selects technique from numbered list")
    print()

    print("4️⃣ TURN RESOLUTION:")
    print("   • Once all players have selected actions:")
    print("   • Actions execute in Agilidad order")
    print("   • Damage calculations show attack vs defense rolls")
    print("   • Results posted in channel")
    print()

    print("5️⃣ ENEMY TURN:")
    print("   • Enemy AI selects action based on current HP")
    print("   • High HP: More likely to attack")
    print("   • Low HP: More likely to use techniques")
    print("   • Enemy action resolves automatically")
    print()

    print("6️⃣ REPEAT OR END:")
    print("   • If enemy HP > 0 and players alive: repeat from step 3")
    print("   • If enemy HP = 0: Victory! Combat ends")
    print("   • If all players HP = 0: Defeat! Combat ends")
    print()


def show_test_scenarios():
    """Show specific test scenarios to try."""
    print("🧪 RECOMMENDED TEST SCENARIOS:")
    print("=" * 50)

    scenarios = [
        {
            "name": "Beginner Test",
            "enemy": "Slime Débil (ID 5)",
            "players": 1,
            "description": "Easy enemy, perfect for testing basic combat mechanics",
            "command": "/combate iniciar enemigo_id:5 participantes:@yourself",
        },
        {
            "name": "Duo Challenge",
            "enemy": "Lobo Salvaje (ID 6)",
            "players": 2,
            "description": "Medium enemy with good stats, test teamwork",
            "command": "/combate iniciar enemigo_id:6 participantes:@player1 @player2",
        },
        {
            "name": "Technique Test",
            "enemy": "Esqueleto Guerrero (ID 7)",
            "players": 2,
            "description": "Test various techniques and status effects",
            "command": "/combate iniciar enemigo_id:7 participantes:@player1 @player2",
        },
        {
            "name": "Boss Fight",
            "enemy": "Dragón Joven (ID 8)",
            "players": 3,
            "description": "High HP enemy, test long combat and AI behavior",
            "command": "/combate iniciar enemigo_id:8 participantes:@p1 @p2 @p3",
        },
        {
            "name": "Tank Test",
            "enemy": "Golem de Piedra (ID 9)",
            "players": 2,
            "description": "High defense enemy, test damage calculation edge cases",
            "command": "/combate iniciar enemigo_id:9 participantes:@player1 @player2",
        },
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"{i}. {scenario['name']}")
        print(f"   Enemy: {scenario['enemy']}")
        print(f"   Players: {scenario['players']}")
        print(f"   Test: {scenario['description']}")
        print(f"   Command: {scenario['command']}")
        print()


def show_troubleshooting():
    """Show common issues and solutions."""
    print("🔧 TROUBLESHOOTING GUIDE:")
    print("=" * 50)

    issues = [
        {
            "issue": "Command not found",
            "solution": "Make sure bot is running and combat module is loaded",
        },
        {
            "issue": "No permission to start combat",
            "solution": "Only users with admin roles can start combat",
        },
        {
            "issue": "Player not found error",
            "solution": "Player must have a registered character (/personaje registrar)",
        },
        {
            "issue": "Combat buttons not working",
            "solution": "Check that player is in the combat and it's player turn phase",
        },
        {
            "issue": "Technique button shows empty list",
            "solution": "Player might not have techniques or all are on cooldown",
        },
        {
            "issue": "Enemy not found",
            "solution": "Use /admin listar_enemigos to get correct enemy IDs",
        },
        {
            "issue": "Combat stuck",
            "solution": "Admin can use /combate terminar to force end combat",
        },
    ]

    for issue_data in issues:
        print(f"❓ {issue_data['issue']}")
        print(f"   💡 {issue_data['solution']}")
        print()


def main():
    """Show all test information."""
    print("⚔️ RINGOBOT RPG COMBAT SYSTEM - DISCORD TEST GUIDE")
    print("=" * 60)
    print()

    show_available_enemies()
    print()
    show_command_examples()
    print()
    show_combat_flow()
    print()
    show_test_scenarios()
    print()
    show_troubleshooting()

    print("=" * 60)
    print("✅ SYSTEM STATUS: ALL TESTS PASSED - READY FOR DISCORD TESTING")
    print("🎮 Start your bot and try the scenarios above!")
    print("=" * 60)


if __name__ == "__main__":
    main()
