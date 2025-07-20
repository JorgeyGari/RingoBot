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
        self.connection_pool = self._initialize_connection_pool()
        self._create_table()

    def _initialize_connection_pool(self) -> "queue.Queue":
        """Initialize a connection pool."""
        from queue import Queue
        pool = Queue(maxsize=10)  # Adjust pool size as needed
        for _ in range(pool.maxsize):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            pool.put(conn)
        logger.info("Connection pool initialized")
        return pool

    def _create_connection(self) -> Optional[sqlite3.Connection]:
        """Fetch a connection from the pool."""
        try:
            return self.connection_pool.get(timeout=5)  # Adjust timeout as needed
        except Exception as e:
            logger.error(f"Error fetching connection from pool: {e}")
            return None

    def _release_connection(self, conn: sqlite3.Connection) -> None:
        """Return a connection to the pool."""
        try:
            self.connection_pool.put(conn, timeout=5)  # Adjust timeout as needed
        except Exception as e:
            logger.error(f"Error returning connection to pool: {e}")
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

                    await ctx.followup.send(
                        "Solicitud de misión enviada.", ephemeral=True
                    )
                    logger.info(
                        f"Quest request created for {player} with ID {request_id}"
                    )
                except Exception as e:
                    logger.error(f"Error sending quest request notification: {e}")
                    await ctx.followup.send(
                        "Solicitud creada, pero no se pudo enviar la notificación.",
                        ephemeral=True,
                    )

        except Exception as e:
            logger.error(f"Error in handle_request_command: {e}")
            await ctx.followup.send("Error al procesar la solicitud.", ephemeral=True)

    async def handle_create_command(
        self, ctx, jugador: str, descripción: str, recompensa: str
    ):
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
                                    discord.EmbedField(
                                        name="Recompensa", value=recompensa
                                    ),
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

            # Get the last message in the channel
            last_message = await ctx.channel.history(limit=1).flatten()
            if last_message:
                last_message_link = last_message[0].jump_url
            else:
                import datetime

                channel_name = ctx.channel.name
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                last_message_link = f"In channel '{channel_name}' at {current_time}"

            # Send completion notification
            import discord

            try:
                completed_channel_id = config.COMPLETED_QUESTS_CHANNEL_ID
                channel = ctx.bot.get_channel(completed_channel_id)

                if channel:
                    embed = discord.Embed(
                        title="Misión completada",
                        description=f"{player} ha completado la misión «{misión}».\n\n[Enlace al último mensaje]({last_message_link})",
                    )
                    message = await channel.send(embed=embed)
                    await message.add_reaction("✅")  # Checkmark reaction
                    await message.add_reaction("❌")  # Cross reaction

                await ctx.followup.send("Misión completada.", ephemeral=True)
                logger.info(f"Quest completed by {player}: {misión}")
            except Exception as e:
                logger.error(f"Error sending completion notification: {e}")
                await ctx.followup.send(
                    "Misión marcada como completada, pero no se pudo enviar la notificación.",
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Error in handle_complete_command: {e}")
            await ctx.followup.send("Error al completar la misión.", ephemeral=True)

    def get_quest_options_for_player(self, player: str) -> List[str]:
        """Get quest options for autocomplete."""
        try:
            records = self.get_user_active_quests(player)
            return [f"{record[0]}: {record[2]}" for record in records if record[2]]
        except Exception as e:
            logger.error(f"Error getting quest options: {e}")
            return []
