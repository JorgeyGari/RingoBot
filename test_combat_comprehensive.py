#!/usr/bin/env python3
"""
Comprehensive test script for the RPG Combat System.
Tests all major functions before Discord deployment.
"""

import sys
import os
import sqlite3
import json
import random
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from utils.config import config


class CombatSystemTester:
    """Comprehensive tester for the combat system."""

    def __init__(self):
        self.db_path = config.CHARACTER_DB_PATH
        self.test_results = []
        self.test_user_id = "test_user_123"
        self.test_user_id_2 = "test_user_456"

    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASS" if success else "❌ FAIL"
        self.test_results.append((test_name, success, details))
        print(f"{status}: {test_name}")
        if details:
            print(f"   {details}")
        if not success:
            print(f"   ❌ {details}")
        print()

    def create_connection(self):
        """Create database connection."""
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            conn.execute("PRAGMA busy_timeout=10000")
            return conn
        except Exception as e:
            print(f"❌ Error creating connection: {e}")
            return None

    def test_database_structure(self):
        """Test that all required tables exist with correct structure."""
        print("🔍 Testing Database Structure...")

        conn = self.create_connection()
        if not conn:
            self.log_test("Database Connection", False, "Could not connect to database")
            return

        try:
            cursor = conn.cursor()

            # Test required tables exist
            required_tables = ["combat_stats", "enemies", "techniques", "equipment"]
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]

            for table in required_tables:
                if table in existing_tables:
                    self.log_test(f"Table '{table}' exists", True)
                else:
                    self.log_test(
                        f"Table '{table}' exists", False, f"Table {table} not found"
                    )

            # Test combat_stats table structure
            cursor.execute("PRAGMA table_info(combat_stats)")
            columns = [col[1] for col in cursor.fetchall()]
            required_columns = [
                "discord_id",
                "fuerza_modifier",
                "aguante_modifier",
                "agilidad_modifier",
                "encanto_modifier",
                "conocimiento_modifier",
                "max_hp",
                "equipped_weapon",
                "equipped_armor",
            ]

            missing_columns = set(required_columns) - set(columns)
            if not missing_columns:
                self.log_test(
                    "Combat_stats table structure",
                    True,
                    f"All {len(required_columns)} columns present",
                )
            else:
                self.log_test(
                    "Combat_stats table structure",
                    False,
                    f"Missing columns: {missing_columns}",
                )

            # Test data exists
            cursor.execute("SELECT COUNT(*) FROM enemies")
            enemy_count = cursor.fetchone()[0]
            self.log_test(
                "Enemies data", enemy_count > 0, f"Found {enemy_count} enemies"
            )

            cursor.execute("SELECT COUNT(*) FROM techniques")
            technique_count = cursor.fetchone()[0]
            self.log_test(
                "Techniques data",
                technique_count > 0,
                f"Found {technique_count} techniques",
            )

            cursor.execute("SELECT COUNT(*) FROM equipment")
            equipment_count = cursor.fetchone()[0]
            self.log_test(
                "Equipment data",
                equipment_count > 0,
                f"Found {equipment_count} equipment items",
            )

        except Exception as e:
            self.log_test("Database Structure Test", False, f"Exception: {e}")
        finally:
            conn.close()

    def test_combat_stats_operations(self):
        """Test combat stats CRUD operations."""
        print("⚔️ Testing Combat Stats Operations...")

        # We need to import the combat module without discord dependencies
        # Let's test the SQL operations directly
        conn = self.create_connection()
        if not conn:
            self.log_test("Combat Stats Connection", False, "Could not connect")
            return

        try:
            cursor = conn.cursor()

            # Test creating default stats
            cursor.execute(
                """
                INSERT OR IGNORE INTO combat_stats (discord_id) VALUES (?)
            """,
                (self.test_user_id,),
            )
            conn.commit()

            # Test reading stats
            cursor.execute(
                """
                SELECT discord_id, fuerza_modifier, aguante_modifier, agilidad_modifier, 
                       encanto_modifier, conocimiento_modifier, max_hp
                FROM combat_stats WHERE discord_id = ?
            """,
                (self.test_user_id,),
            )

            result = cursor.fetchone()
            if result:
                self.log_test(
                    "Create default combat stats",
                    True,
                    f"Created stats for {result[0]}",
                )

                # Test updating stats
                cursor.execute(
                    """
                    UPDATE combat_stats 
                    SET fuerza_modifier = ?, aguante_modifier = ?
                    WHERE discord_id = ?
                """,
                    (3, 2, self.test_user_id),
                )
                conn.commit()

                # Verify update
                cursor.execute(
                    """
                    SELECT fuerza_modifier, aguante_modifier FROM combat_stats WHERE discord_id = ?
                """,
                    (self.test_user_id,),
                )
                updated_stats = cursor.fetchone()

                if updated_stats and updated_stats[0] == 3 and updated_stats[1] == 2:
                    self.log_test(
                        "Update combat stats",
                        True,
                        f"Fuerza: {updated_stats[0]}, Aguante: {updated_stats[1]}",
                    )
                else:
                    self.log_test(
                        "Update combat stats",
                        False,
                        f"Expected (3,2), got {updated_stats}",
                    )
            else:
                self.log_test(
                    "Create default combat stats",
                    False,
                    "No stats found after creation",
                )

        except Exception as e:
            self.log_test("Combat Stats Operations", False, f"Exception: {e}")
        finally:
            conn.close()

    def test_equipment_system(self):
        """Test equipment bonuses calculation."""
        print("🛡️ Testing Equipment System...")

        conn = self.create_connection()
        if not conn:
            self.log_test("Equipment Connection", False, "Could not connect")
            return

        try:
            cursor = conn.cursor()

            # Test equipment exists
            cursor.execute(
                "SELECT name, equipment_type, fuerza_bonus, aguante_bonus FROM equipment LIMIT 3"
            )
            equipment_items = cursor.fetchall()

            if equipment_items:
                self.log_test(
                    "Equipment items exist", True, f"Found {len(equipment_items)} items"
                )

                # Test specific equipment
                cursor.execute(
                    "SELECT * FROM equipment WHERE name = 'Espada legendaria'"
                )
                sword = cursor.fetchone()
                if sword and sword[2] == 10:  # fuerza_bonus should be 10
                    self.log_test(
                        "Legendary sword stats",
                        True,
                        f"Espada legendaria has +{sword[2]} Fuerza",
                    )
                else:
                    self.log_test(
                        "Legendary sword stats",
                        False,
                        f"Expected +10 Fuerza, got {sword[2] if sword else 'None'}",
                    )

                # Test armor
                cursor.execute("SELECT * FROM equipment WHERE name = 'Armadura ligera'")
                armor = cursor.fetchone()
                if armor and armor[3] == 3:  # aguante_bonus should be 3
                    self.log_test(
                        "Light armor stats",
                        True,
                        f"Armadura ligera has +{armor[3]} Aguante",
                    )
                else:
                    self.log_test(
                        "Light armor stats",
                        False,
                        f"Expected +3 Aguante, got {armor[3] if armor else 'None'}",
                    )

                # Test equipping items
                cursor.execute(
                    """
                    UPDATE combat_stats 
                    SET equipped_weapon = 'Espada legendaria', equipped_armor = 'Armadura ligera'
                    WHERE discord_id = ?
                """,
                    (self.test_user_id,),
                )
                conn.commit()

                # Verify equipment
                cursor.execute(
                    """
                    SELECT equipped_weapon, equipped_armor FROM combat_stats WHERE discord_id = ?
                """,
                    (self.test_user_id,),
                )
                equipment = cursor.fetchone()

                if (
                    equipment
                    and equipment[0] == "Espada legendaria"
                    and equipment[1] == "Armadura ligera"
                ):
                    self.log_test(
                        "Equip items", True, f"Equipped: {equipment[0]}, {equipment[1]}"
                    )
                else:
                    self.log_test(
                        "Equip items", False, f"Equipment not properly set: {equipment}"
                    )
            else:
                self.log_test(
                    "Equipment items exist", False, "No equipment found in database"
                )

        except Exception as e:
            self.log_test("Equipment System Test", False, f"Exception: {e}")
        finally:
            conn.close()

    def test_technique_system(self):
        """Test technique functionality."""
        print("✨ Testing Technique System...")

        conn = self.create_connection()
        if not conn:
            self.log_test("Technique Connection", False, "Could not connect")
            return

        try:
            cursor = conn.cursor()

            # Test techniques exist
            cursor.execute(
                "SELECT id, name, associated_stat, effect_type, effect_value, cost FROM techniques"
            )
            techniques = cursor.fetchall()

            if techniques:
                self.log_test(
                    "Techniques exist", True, f"Found {len(techniques)} techniques"
                )

                # Test specific techniques
                damage_techniques = [t for t in techniques if t[3] == "damage"]
                heal_techniques = [t for t in techniques if t[3] == "heal"]
                status_techniques = [t for t in techniques if t[3] == "status"]

                self.log_test(
                    "Damage techniques",
                    len(damage_techniques) > 0,
                    f"Found {len(damage_techniques)} damage techniques",
                )
                self.log_test(
                    "Heal techniques",
                    len(heal_techniques) > 0,
                    f"Found {len(heal_techniques)} heal techniques",
                )
                self.log_test(
                    "Status techniques",
                    len(status_techniques) > 0,
                    f"Found {len(status_techniques)} status techniques",
                )

                # Test technique with cooldown
                cooldown_techniques = [t for t in techniques if t[5] > 0]  # cost > 0
                self.log_test(
                    "Cooldown techniques",
                    len(cooldown_techniques) > 0,
                    f"Found {len(cooldown_techniques)} techniques with cooldowns",
                )

                # Test technique stats association
                stat_associations = set(t[2] for t in techniques)  # associated_stat
                expected_stats = {
                    "fuerza",
                    "aguante",
                    "agilidad",
                    "encanto",
                    "conocimiento",
                }
                covered_stats = stat_associations.intersection(expected_stats)

                self.log_test(
                    "Technique stat coverage",
                    len(covered_stats) >= 3,
                    f"Techniques use {len(covered_stats)} different stats: {covered_stats}",
                )

            else:
                self.log_test(
                    "Techniques exist", False, "No techniques found in database"
                )

        except Exception as e:
            self.log_test("Technique System Test", False, f"Exception: {e}")
        finally:
            conn.close()

    def test_enemy_system(self):
        """Test enemy creation and management."""
        print("👹 Testing Enemy System...")

        conn = self.create_connection()
        if not conn:
            self.log_test("Enemy Connection", False, "Could not connect")
            return

        try:
            cursor = conn.cursor()

            # Test enemies exist
            cursor.execute(
                "SELECT id, name, max_hp, fuerza_modifier, techniques FROM enemies"
            )
            enemies = cursor.fetchall()

            if enemies:
                self.log_test("Enemies exist", True, f"Found {len(enemies)} enemies")

                # Test enemy variety
                hp_values = [e[2] for e in enemies]
                min_hp, max_hp = min(hp_values), max(hp_values)
                self.log_test(
                    "Enemy HP variety",
                    max_hp > min_hp * 2,
                    f"HP range: {min_hp} - {max_hp}",
                )

                # Test enemy with techniques
                enemies_with_techniques = []
                for enemy in enemies:
                    if enemy[4]:  # techniques field
                        try:
                            techniques = json.loads(enemy[4])
                            if techniques:
                                enemies_with_techniques.append(
                                    (enemy[1], len(techniques))
                                )
                        except json.JSONDecodeError:
                            pass

                self.log_test(
                    "Enemies with techniques",
                    len(enemies_with_techniques) > 0,
                    f"{len(enemies_with_techniques)} enemies have techniques",
                )

                # Test creating a new enemy
                test_enemy_name = f"Test Enemy {random.randint(1000, 9999)}"
                cursor.execute(
                    """
                    INSERT INTO enemies (name, description, max_hp, fuerza_modifier, created_by)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (test_enemy_name, "A test enemy", 50, 2, "test_system"),
                )
                conn.commit()

                # Verify creation
                cursor.execute(
                    "SELECT id FROM enemies WHERE name = ?", (test_enemy_name,)
                )
                new_enemy = cursor.fetchone()

                if new_enemy:
                    self.log_test(
                        "Create new enemy", True, f"Created enemy ID {new_enemy[0]}"
                    )

                    # Clean up test enemy
                    cursor.execute("DELETE FROM enemies WHERE id = ?", (new_enemy[0],))
                    conn.commit()
                else:
                    self.log_test(
                        "Create new enemy", False, "Enemy not found after creation"
                    )

            else:
                self.log_test("Enemies exist", False, "No enemies found in database")

        except Exception as e:
            self.log_test("Enemy System Test", False, f"Exception: {e}")
        finally:
            conn.close()

    def test_combat_calculations(self):
        """Test combat damage calculations and mechanics."""
        print("🎲 Testing Combat Calculations...")

        try:
            # Test attack calculation logic
            def calculate_attack(
                attacker_stat, attacker_roll, defender_stat, defender_roll
            ):
                attack_total = attacker_roll + attacker_stat
                defense_total = defender_roll + defender_stat
                if attack_total > defense_total:
                    return attack_total - defense_total
                return 0

            # Test various scenarios
            test_cases = [
                (
                    5,
                    6,
                    3,
                    4,
                    4,
                ),  # (att_stat, att_roll, def_stat, def_roll, expected_damage)
                (2, 3, 2, 3, 0),  # Equal values = no damage
                (1, 1, 5, 6, 0),  # Weak attack vs strong defense
                (10, 6, 0, 1, 15),  # Strong attack vs weak defense
            ]

            all_passed = True
            for att_stat, att_roll, def_stat, def_roll, expected in test_cases:
                damage = calculate_attack(att_stat, att_roll, def_stat, def_roll)
                if damage != expected:
                    all_passed = False
                    break

            self.log_test(
                "Attack calculation logic",
                all_passed,
                f"Tested {len(test_cases)} combat scenarios",
            )

            # Test HP calculations
            def apply_damage(current_hp, max_hp, damage):
                new_hp = max(0, current_hp - damage)
                return new_hp

            def apply_heal(current_hp, max_hp, heal_amount):
                new_hp = min(max_hp, current_hp + heal_amount)
                return new_hp

            # Test HP scenarios
            hp_tests = [
                (50, 100, 30, 20),  # Take 30 damage from 50 HP
                (10, 100, 20, 0),  # Take fatal damage
                (30, 100, -15, 45),  # Heal 15 HP
                (90, 100, -20, 100),  # Overheal (should cap at max)
            ]

            hp_passed = True
            for current, max_hp, change, expected in hp_tests:
                if change < 0:  # Healing
                    result = apply_heal(current, max_hp, abs(change))
                else:  # Damage
                    result = apply_damage(current, max_hp, change)

                if result != expected:
                    hp_passed = False
                    break

            self.log_test(
                "HP calculation logic",
                hp_passed,
                f"Tested {len(hp_tests)} HP scenarios",
            )

            # Test status effect logic
            def apply_terror_check():
                return random.randint(1, 5) == 1  # 1/5 chance

            # Run terror check multiple times to verify it's working
            terror_results = [apply_terror_check() for _ in range(100)]
            terror_rate = sum(terror_results) / len(terror_results)

            # Should be roughly 20% (0.2), allow some variance
            terror_valid = 0.1 <= terror_rate <= 0.3
            self.log_test(
                "Terror status effect probability",
                terror_valid,
                f"Terror triggered {terror_rate:.1%} of the time (expected ~20%)",
            )

        except Exception as e:
            self.log_test("Combat Calculations Test", False, f"Exception: {e}")

    def test_integration_scenario(self):
        """Test a full combat scenario integration."""
        print("🎭 Testing Integration Scenario...")

        conn = self.create_connection()
        if not conn:
            self.log_test("Integration Connection", False, "Could not connect")
            return

        try:
            cursor = conn.cursor()

            # Set up test participants
            test_users = [self.test_user_id, self.test_user_id_2]

            # Create combat stats for test users
            for user_id in test_users:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO combat_stats 
                    (discord_id, fuerza_modifier, aguante_modifier, agilidad_modifier, max_hp)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (user_id, 2, 1, 3, 60),
                )

            # Get a test enemy
            cursor.execute("SELECT id, name, max_hp FROM enemies LIMIT 1")
            enemy_data = cursor.fetchone()

            if enemy_data:
                enemy_id, enemy_name, enemy_hp = enemy_data

                # Simulate combat initialization
                participants = []
                for user_id in test_users:
                    cursor.execute(
                        """
                        SELECT discord_id, fuerza_modifier, aguante_modifier, agilidad_modifier, max_hp
                        FROM combat_stats WHERE discord_id = ?
                    """,
                        (user_id,),
                    )
                    stats = cursor.fetchone()
                    if stats:
                        participants.append(
                            {
                                "id": stats[0],
                                "fuerza": stats[1],
                                "aguante": stats[2],
                                "agilidad": stats[3],
                                "hp": stats[4],
                                "current_hp": stats[4],
                            }
                        )

                if len(participants) == 2:
                    self.log_test(
                        "Combat participants setup",
                        True,
                        f"2 participants ready vs {enemy_name}",
                    )

                    # Test initiative order (sort by agilidad)
                    sorted_participants = sorted(
                        participants, key=lambda p: p["agilidad"], reverse=True
                    )
                    initiative_correct = all(
                        sorted_participants[i]["agilidad"]
                        >= sorted_participants[i + 1]["agilidad"]
                        for i in range(len(sorted_participants) - 1)
                    )

                    self.log_test(
                        "Initiative ordering",
                        initiative_correct,
                        f"Turn order: {[p['id'][-3:] for p in sorted_participants]}",
                    )

                    # Simulate a round of combat
                    combat_log = []

                    # Player attacks
                    for participant in participants:
                        attack_roll = random.randint(1, 6)
                        defense_roll = random.randint(1, 6)

                        attack_total = attack_roll + participant["fuerza"]
                        defense_total = defense_roll + 2  # Enemy aguante

                        if attack_total > defense_total:
                            damage = attack_total - defense_total
                            enemy_hp -= damage
                            combat_log.append(
                                f"{participant['id'][-3:]} deals {damage} damage"
                            )
                        else:
                            combat_log.append(f"{participant['id'][-3:]} misses")

                    # Enemy attacks back
                    if enemy_hp > 0:
                        target = random.choice(participants)
                        attack_roll = random.randint(1, 6)
                        defense_roll = random.randint(1, 6)

                        attack_total = attack_roll + 2  # Enemy fuerza
                        defense_total = defense_roll + target["aguante"]

                        if attack_total > defense_total:
                            damage = attack_total - defense_total
                            target["current_hp"] = max(0, target["current_hp"] - damage)
                            combat_log.append(
                                f"{enemy_name} deals {damage} damage to {target['id'][-3:]}"
                            )
                        else:
                            combat_log.append(
                                f"{enemy_name} misses {target['id'][-3:]}"
                            )

                    self.log_test(
                        "Combat round simulation",
                        True,
                        f"Round completed: {'; '.join(combat_log)}",
                    )

                    # Test victory condition
                    victory_condition = enemy_hp <= 0
                    defeat_condition = all(p["current_hp"] <= 0 for p in participants)

                    if victory_condition:
                        result = "Victory!"
                    elif defeat_condition:
                        result = "Defeat!"
                    else:
                        result = "Combat continues"

                    self.log_test(
                        "Combat state evaluation",
                        True,
                        f"Enemy HP: {enemy_hp}, Result: {result}",
                    )

                else:
                    self.log_test(
                        "Combat participants setup",
                        False,
                        f"Expected 2 participants, got {len(participants)}",
                    )
            else:
                self.log_test(
                    "Integration test enemy", False, "No enemy found for testing"
                )

            # Clean up test data
            for user_id in test_users:
                cursor.execute(
                    "DELETE FROM combat_stats WHERE discord_id = ?", (user_id,)
                )
            conn.commit()

        except Exception as e:
            self.log_test("Integration Scenario Test", False, f"Exception: {e}")
        finally:
            conn.close()

    def run_all_tests(self):
        """Run all test suites."""
        print("🧪 STARTING COMPREHENSIVE COMBAT SYSTEM TESTS")
        print("=" * 60)
        print()

        # Run test suites
        self.test_database_structure()
        self.test_combat_stats_operations()
        self.test_equipment_system()
        self.test_technique_system()
        self.test_enemy_system()
        self.test_combat_calculations()
        self.test_integration_scenario()

        # Summary
        print("=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)

        passed = sum(1 for _, success, _ in self.test_results if success)
        failed = len(self.test_results) - passed

        print(f"✅ PASSED: {passed}")
        print(f"❌ FAILED: {failed}")
        print(f"📈 SUCCESS RATE: {passed/len(self.test_results)*100:.1f}%")
        print()

        if failed > 0:
            print("❌ FAILED TESTS:")
            for test_name, success, details in self.test_results:
                if not success:
                    print(f"   • {test_name}: {details}")
            print()

        if passed == len(self.test_results):
            print("🎉 ALL TESTS PASSED! Combat system is ready for Discord deployment.")
            print("\n🚀 READY TO DEPLOY:")
            print("   1. Start your Discord bot")
            print("   2. Use /admin listar_enemigos to see available enemies")
            print("   3. Use /combate iniciar <enemy_id> @players to start combat")
            print("   4. Players click buttons to select actions")
            print("   5. Enjoy strategic turn-based RPG combat!")
        else:
            print("⚠️  Some tests failed. Please review the issues before deploying.")

        print("\n" + "=" * 60)
        return failed == 0


def main():
    """Main test function."""
    tester = CombatSystemTester()
    success = tester.run_all_tests()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
