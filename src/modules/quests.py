"""
Quests module for quest management functionality.
"""

import datetime
import logging
import sqlite3

import discord

from utils.config import config
from utils.parse import to_int

logger = logging.getLogger(__name__)


class QuestsModule:
    """Handles quest management functionality."""

    CREATE_TABLE_QUESTS = """CREATE TABLE IF NOT EXISTS quests (
        id integer PRIMARY KEY,
        player text NOT NULL,
        description text NULL,
        reward text NULL,
        status text DEFAULT 'pending',
        completed_by text NULL,
        completed_at timestamp NULL
    );"""

    def __init__(self, db_path: str | None = None):
        """Initialize the quests module."""
        self.db_path = db_path or config.QUEST_DB_PATH
        # ponytail: one shared connection. sqlite3 serializes access itself and
        # every caller runs on the bot's event loop thread. Pool it if writes
        # ever move off that thread and contend.
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_table()

    def _create_table(self) -> None:
        """Create the quests table if it doesn't exist, then migrate old files."""
        try:
            with self.conn:
                self.conn.execute(self.CREATE_TABLE_QUESTS)
                columns = {row[1] for row in self.conn.execute("PRAGMA table_info(quests)")}
                if "status" not in columns:
                    self.conn.execute("ALTER TABLE quests ADD COLUMN status text DEFAULT 'pending'")
                if "completed_by" not in columns:
                    self.conn.execute("ALTER TABLE quests ADD COLUMN completed_by text NULL")
                if "completed_at" not in columns:
                    self.conn.execute("ALTER TABLE quests ADD COLUMN completed_at timestamp NULL")
            logger.info("Quests table created/verified")
        except sqlite3.Error as e:
            logger.error(f"Error creating table: {e}")

    def create_request(self, player: str) -> int:
        """
        Create a new quest request for a player.

        Args:
            player: Player identifier

        Returns:
            Quest ID if successful, -1 if player already has pending request
        """
        try:
            # Check for existing pending request
            existing_sql = (
                """SELECT * FROM quests WHERE player=? AND description IS NULL AND reward IS NULL"""
            )
            if self.conn.execute(existing_sql, (player,)).fetchone():
                logger.info(f"Player {player} already has pending quest request")
                return -1

            # Insert new request
            sql = """INSERT INTO quests(player, description, reward) VALUES(?,?,?)"""
            with self.conn:
                quest_id = self.conn.execute(sql, (player, None, None)).lastrowid

            logger.info(f"Created quest request {quest_id} for player {player}")
            return quest_id or -1

        except sqlite3.Error as e:
            logger.error(f"Error creating quest request: {e}")
            return -1

    def get_users_with_pending_requests(self) -> list[str]:
        """Get list of users with pending quest requests."""
        try:
            sql = """SELECT player FROM quests WHERE description IS NULL AND reward IS NULL"""
            return [row[0] for row in self.conn.execute(sql)]
        except sqlite3.Error as e:
            logger.error(f"Error getting pending requests: {e}")
            return []

    def get_user_request_id(self, player: str) -> int | None:
        """Get the quest request ID for a player."""
        try:
            sql = """SELECT id FROM quests WHERE player=? AND description IS NULL AND reward IS NULL"""
            row = self.conn.execute(sql, (player,)).fetchone()
            return row[0] if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting user request ID: {e}")
            return None

    def get_user_active_quests(self, player: str) -> list[tuple]:
        """Get active quests for a player."""
        try:
            # Active = still has description/reward and was not finished or dropped
            sql = """SELECT * FROM quests WHERE player=? AND description IS NOT NULL
                     AND reward IS NOT NULL
                     AND COALESCE(status, 'pending') NOT IN ('completed', 'abandoned')"""
            return self.conn.execute(sql, (player,)).fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting active quests: {e}")
            return []

    def get_active_quest(self, quest_id: int, player: str) -> tuple | None:
        """Get one still-active quest of a player by id."""
        try:
            sql = """SELECT * FROM quests WHERE id=? AND player=?
                     AND description IS NOT NULL AND reward IS NOT NULL
                     AND COALESCE(status, 'pending') NOT IN ('completed', 'abandoned')"""
            return self.conn.execute(sql, (quest_id, player)).fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error getting quest {quest_id}: {e}")
            return None

    def complete_quest(self, quest_id: int, player: str, completed_by: str) -> bool:
        """Mark a quest as completed. Returns False if it was not active."""
        try:
            sql = """UPDATE quests SET status='completed', completed_by=?,
                     completed_at=CURRENT_TIMESTAMP
                     WHERE id=? AND player=? AND description IS NOT NULL
                     AND reward IS NOT NULL
                     AND COALESCE(status, 'pending') NOT IN ('completed', 'abandoned')"""
            with self.conn:
                updated = self.conn.execute(sql, (completed_by, quest_id, player)).rowcount
            logger.info(f"Quest {quest_id} completed by {player}")
            return updated > 0
        except sqlite3.Error as e:
            logger.error(f"Error completing quest {quest_id}: {e}")
            return False

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
        try:
            request_id = self.get_user_request_id(player)
            if not request_id:
                return False

            sql = """UPDATE quests SET description = ?, reward = ? WHERE id = ?"""
            with self.conn:
                self.conn.execute(sql, (description, reward, request_id))

            logger.info(f"Updated quest {request_id} for player {player}")
            return True

        except sqlite3.Error as e:
            logger.error(f"Error updating quest request: {e}")
            return False

    async def handle_request_command(self, ctx):
        """Handle the quest request command."""
        try:
            await ctx.defer()

            player = ctx.user.name
            request_id = self.create_request(player)

            if request_id == -1:
                await ctx.followup.send(
                    "Ya tienes una solicitud de misión en curso.", ephemeral=True
                )
            else:
                # Send a message to the quest-requests channel
                import discord

                try:
                    channel_id = config.QUEST_REQUESTS_CHANNEL_ID
                    channel = ctx.bot.get_channel(channel_id)

                    if channel:
                        embed = discord.Embed(
                            title="Nueva solicitud de misión",
                            description=f"**Solicitante:** {player}",
                        )
                        await channel.send(embed=embed)

                    await ctx.followup.send("Solicitud de misión enviada.", ephemeral=True)
                    logger.info(f"Quest request created for {player} with ID {request_id}")
                except Exception as e:
                    logger.error(f"Error sending quest request notification: {e}")
                    await ctx.followup.send(
                        "Solicitud creada, pero no se pudo enviar la notificación.",
                        ephemeral=True,
                    )

        except Exception as e:
            logger.error(f"Error in handle_request_command: {e}")
            await ctx.followup.send("Error al procesar la solicitud.", ephemeral=True)

    async def handle_create_command(self, ctx, jugador: str, descripción: str, recompensa: str):
        """Handle the quest creation command."""
        try:
            await ctx.defer()

            request_id = self.get_user_request_id(jugador)
            if not request_id:
                await ctx.followup.send(
                    "El jugador no tiene una solicitud pendiente.", ephemeral=True
                )
                return

            success = self.update_request(jugador, descripción, recompensa)
            if success:
                # Send a message to the user's quest channel
                import discord

                try:
                    # Check if user has a configured quest channel
                    quest_channels = getattr(config, "QUEST_CHANNEL_ID_DICT", {})
                    if jugador in quest_channels:
                        channel = ctx.bot.get_channel(quest_channels[jugador])
                        if channel:
                            embed = discord.Embed(
                                title=descripción,
                                fields=[
                                    discord.EmbedField(name="Recompensa", value=recompensa),
                                ],
                            )
                            embed.set_author(name=f"Misión n.º {request_id}")
                            await channel.send(embed=embed)

                    await ctx.followup.send("Misión creada.")
                    logger.info(f"Quest created for {jugador}: {descripción}")
                except Exception as e:
                    logger.error(f"Error sending quest to player channel: {e}")
                    await ctx.followup.send(
                        "Misión creada, pero no se pudo enviar al jugador.",
                        ephemeral=True,
                    )
            else:
                await ctx.followup.send("Error al crear la misión.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error in handle_create_command: {e}")
            await ctx.followup.send("Error al crear la misión.", ephemeral=True)

    async def handle_complete_command(self, ctx, misión: str):
        """Handle the quest completion command."""
        try:
            await ctx.defer()

            player = ctx.user.name

            # Autocomplete hands over "id: description"
            quest_id = to_int(misión.split(":")[0], -1)
            quest = self.get_active_quest(quest_id, player) if quest_id > 0 else None
            if not quest:
                await ctx.followup.send("No encuentro esa misión entre las tuyas.", ephemeral=True)
                return

            # Get the last message in the channel
            last_message = await ctx.channel.history(limit=1).flatten()
            if last_message:
                last_message_link = last_message[0].jump_url
            else:
                channel_name = ctx.channel.name
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                last_message_link = f"In channel '{channel_name}' at {current_time}"

            # Send completion notification
            try:
                completed_channel_id = config.COMPLETED_QUESTS_CHANNEL_ID
                channel = ctx.bot.get_channel(completed_channel_id)

                if channel:
                    embed = discord.Embed(
                        title="Misión completada",
                        description=f"{player} ha completado la misión «{quest[2]}».\n\n[Enlace al último mensaje]({last_message_link})",
                    )
                    message = await channel.send(embed=embed)
                    await message.add_reaction("✅")  # Checkmark reaction
                    await message.add_reaction("❌")  # Cross reaction

                if not self.complete_quest(quest_id, player, str(ctx.user.id)):
                    await ctx.followup.send(
                        "No se pudo marcar la misión como completada.", ephemeral=True
                    )
                    return

                await ctx.followup.send("Misión completada.", ephemeral=True)
                logger.info(f"Quest completed by {player}: {quest[2]}")
            except Exception as e:
                logger.error(f"Error sending completion notification: {e}")
                await ctx.followup.send(
                    "Misión marcada como completada, pero no se pudo enviar la notificación.",
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Error in handle_complete_command: {e}")
            await ctx.followup.send("Error al completar la misión.", ephemeral=True)

    def get_quest_options_for_player(self, player: str) -> list[str]:
        """Get quest options for autocomplete."""
        try:
            records = self.get_user_active_quests(player)
            return [f"{record[0]}: {record[2]}" for record in records if record[2]]
        except Exception as e:
            logger.error(f"Error getting quest options: {e}")
            return []


if __name__ == "__main__":  # self-check: cd src && python -m modules.quests
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        quests = QuestsModule(str(Path(tmp) / "quests.db"))
        assert quests.get_user_active_quests("ana") == []

        quests.create_request("ana")
        assert quests.get_user_active_quests("ana") == []
        assert quests.update_request("ana", "robar la galleta", "3 PC")
        active = quests.get_user_active_quests("ana")
        assert [row[2] for row in active] == ["robar la galleta"]

        quest_id = active[0][0]
        assert quests.get_active_quest(quest_id, "beto") is None
        assert quests.complete_quest(quest_id, "ana", "123")
        assert quests.get_user_active_quests("ana") == []
        assert not quests.complete_quest(quest_id, "ana", "123")

        # Old databases without the status column get migrated
        path = Path(tmp) / "old.db"
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE quests (id integer PRIMARY KEY, player text NOT NULL, "
            "description text NULL, reward text NULL)"
        )
        conn.execute(
            "INSERT INTO quests(player, description, reward) VALUES('ana', 'vieja', '1 PC')"
        )
        conn.commit()
        conn.close()
        old = QuestsModule(str(path))
        assert [row[2] for row in old.get_user_active_quests("ana")] == ["vieja"]

    print("quests self-check ok")
