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
        reward text NULL,
        status text DEFAULT 'pending',
        completion_message_id text NULL,
        completed_by text NULL,
        completed_at timestamp NULL
    );"""

    def __init__(self):
        """Initialize the quests module."""
        self.db_path = config.QUEST_DB_PATH
        # ponytail: one shared connection. sqlite3 serializes access itself and
        # every caller runs on the bot's event loop thread. Pool it if writes
        # ever move off that thread and contend.
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_table()

    def _create_table(self) -> None:
        """Create the quests table if it doesn't exist."""
        try:
            with self.conn:
                self.conn.execute(self.CREATE_TABLE_QUESTS)
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
            existing_sql = """SELECT * FROM quests WHERE player=? AND description IS NULL AND reward IS NULL"""
            if self.conn.execute(existing_sql, (player,)).fetchone():
                logger.info(f"Player {player} already has pending quest request")
                return -1

            # Insert new request
            sql = """INSERT INTO quests(player, description, reward) VALUES(?,?,?)"""
            with self.conn:
                quest_id = self.conn.execute(sql, (player, None, None)).lastrowid

            logger.info(f"Created quest request {quest_id} for player {player}")
            return quest_id

        except sqlite3.Error as e:
            logger.error(f"Error creating quest request: {e}")
            return -1

    def get_users_with_pending_requests(self) -> List[str]:
        """Get list of users with pending quest requests."""
        try:
            sql = """SELECT player FROM quests WHERE description IS NULL AND reward IS NULL"""
            return [row[0] for row in self.conn.execute(sql)]
        except sqlite3.Error as e:
            logger.error(f"Error getting pending requests: {e}")
            return []

    def get_user_request_id(self, player: str) -> Optional[int]:
        """Get the quest request ID for a player."""
        try:
            sql = """SELECT id FROM quests WHERE player=? AND description IS NULL AND reward IS NULL"""
            row = self.conn.execute(sql, (player,)).fetchone()
            return row[0] if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting user request ID: {e}")
            return None

    def get_user_active_quests(self, player: str) -> List[Tuple]:
        """Get active quests for a player."""
        try:
            sql = """SELECT * FROM quests WHERE player=? AND description IS NOT NULL AND reward IS NOT NULL
                     AND (status = 'active' OR status IS NULL OR status = 'pending')"""
            return self.conn.execute(sql, (player,)).fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error getting active quests: {e}")
            return []

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

            sql = """UPDATE quests SET description = ?, reward = ?, status = 'active' WHERE id = ?"""
            with self.conn:
                self.conn.execute(sql, (description, reward, request_id))

            logger.info(f"Updated quest {request_id} for player {player}")
            return True

        except sqlite3.Error as e:
            logger.error(f"Error updating quest request: {e}")
            return False

    def mark_quest_as_completed(
        self, quest_id: int, player: str, message_id: str
    ) -> bool:
        """Mark a quest as completed and awaiting approval."""
        try:
            sql = """UPDATE quests SET status = 'completed', completed_by = ?,
                     completion_message_id = ?, completed_at = CURRENT_TIMESTAMP
                     WHERE id = ?"""
            with self.conn:
                cursor = self.conn.execute(sql, (player, message_id, quest_id))

            logger.info(f"Quest {quest_id} marked as completed by {player}")
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error marking quest as completed: {e}")
            return False

    def get_quest_by_message_id(self, message_id: str) -> Optional[Tuple]:
        """Get quest information by completion message ID."""
        try:
            sql = """SELECT id, player, description, reward, completed_by, status
                     FROM quests WHERE completion_message_id = ?"""
            return self.conn.execute(sql, (message_id,)).fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error getting quest by message ID: {e}")
            return None

    def approve_quest(self, quest_id: int) -> bool:
        """Approve a completed quest."""
        try:
            sql = """UPDATE quests SET status = 'approved' WHERE id = ?"""
            with self.conn:
                cursor = self.conn.execute(sql, (quest_id,))

            logger.info(f"Quest {quest_id} approved")
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error approving quest: {e}")
            return False

    def reject_quest(self, quest_id: int) -> bool:
        """Reject a completed quest and mark as active again."""
        try:
            sql = """UPDATE quests SET status = 'active', completed_by = NULL,
                     completion_message_id = NULL, completed_at = NULL
                     WHERE id = ?"""
            with self.conn:
                cursor = self.conn.execute(sql, (quest_id,))

            logger.info(f"Quest {quest_id} rejected and marked as active")
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error rejecting quest: {e}")
            return False

    def get_quest_by_id_and_player(self, quest_id: int, player: str) -> Optional[Tuple]:
        """Get a specific quest by ID and player."""
        try:
            sql = """SELECT id, player, description, reward, status
                     FROM quests WHERE id = ? AND player = ? AND description IS NOT NULL AND reward IS NOT NULL"""
            return self.conn.execute(sql, (quest_id, player)).fetchone()
        except sqlite3.Error as e:
            logger.error(f"Error getting quest: {e}")
            return None

    def abandon_quest(self, quest_id: int, player: str) -> bool:
        """Allow a player to abandon/give up on an active quest."""
        conn = self._create_connection()
        if not conn:
            return False

        try:
            cursor = conn.cursor()

            # Verify the quest belongs to the player and is active
            cursor.execute(
                """
                SELECT id, status FROM quests 
                WHERE id = ? AND player = ? AND description IS NOT NULL AND reward IS NOT NULL
            """,
                (quest_id, player),
            )
            quest_data = cursor.fetchone()

            if not quest_data:
                logger.warning(
                    f"Quest {quest_id} not found or doesn't belong to {player}"
                )
                return False

            quest_status = quest_data[1]
            if quest_status not in ["active", "pending", None]:
                logger.warning(
                    f"Quest {quest_id} cannot be abandoned - current status: {quest_status}"
                )
                return False

            # Mark the quest as abandoned instead of deleting
            cursor.execute(
                """
                UPDATE quests SET status = 'abandoned', completed_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """,
                (quest_id,),
            )
            conn.commit()

            logger.info(f"Quest {quest_id} abandoned by {player}")
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Error abandoning quest: {e}")
            return False
        finally:
            conn.close()

    async def handle_quest_approval(self, bot, message_id: str, user_id: str) -> bool:
        """Handle quest approval by admin."""
        try:
            quest = self.get_quest_by_message_id(message_id)
            if not quest:
                logger.warning(f"No quest found for message ID {message_id}")
                return False

            quest_id, original_player, description, reward, completed_by, status = quest

            if status != "completed":
                logger.warning(f"Quest {quest_id} is not in completed status")
                return False

            # Approve the quest
            if self.approve_quest(quest_id):
                # Send notification to the user
                try:
                    user = await bot.fetch_user(int(completed_by))
                    if user:
                        import discord

                        embed = discord.Embed(
                            title="🎉 ¡Misión cumplida!",
                            description=f"Has cumplido los requisitos de la misión.",
                            color=discord.Color.green(),
                        )
                        embed.add_field(name="Misión", value=description, inline=False)
                        embed.add_field(name="Recompensa", value=reward, inline=False)
                        embed.set_footer(text="¡Felicidades por completar la misión!")

                        await user.send(embed=embed)
                        logger.info(
                            f"Approval notification sent to user {completed_by}"
                        )
                except Exception as e:
                    logger.error(f"Error sending approval notification: {e}")

                return True

            return False

        except Exception as e:
            logger.error(f"Error handling quest approval: {e}")
            return False

    async def handle_quest_rejection(self, bot, message_id: str, user_id: str) -> bool:
        """Handle quest rejection by admin."""
        try:
            quest = self.get_quest_by_message_id(message_id)
            if not quest:
                logger.warning(f"No quest found for message ID {message_id}")
                return False

            quest_id, original_player, description, reward, completed_by, status = quest

            if status != "completed":
                logger.warning(f"Quest {quest_id} is not in completed status")
                return False

            # Reject the quest (reset to active)
            if self.reject_quest(quest_id):
                # Send notification to the user
                try:
                    user = await bot.fetch_user(int(completed_by))
                    if user:
                        import discord

                        embed = discord.Embed(
                            title="❌ Misión sin cumplir",
                            description=f"No has cumplido los requisitos de la misión.",
                            color=discord.Color.red(),
                        )
                        embed.add_field(name="Misión", value=description, inline=False)
                        embed.add_field(name="Recompensa", value=reward, inline=False)
                        embed.set_footer(
                            text="La misión se te ha vuelto a asignar. Puedes intentar completarla de nuevo."
                        )

                        await user.send(embed=embed)
                        logger.info(
                            f"Rejection notification sent to user {completed_by}"
                        )
                except Exception as e:
                    logger.error(f"Error sending rejection notification: {e}")

                return True

            return False

        except Exception as e:
            logger.error(f"Error handling quest rejection: {e}")
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

            # Extract quest ID from the mission string (format: "ID: Description")
            try:
                quest_id = int(misión.split(":")[0])
            except (ValueError, IndexError):
                await ctx.followup.send(
                    "Formato de misión inválido. Usa el autocompletado para seleccionar una misión.",
                    ephemeral=True,
                )
                return

            # Verify the quest belongs to the user and is active
            quest = self.get_quest_by_id_and_player(quest_id, player)
            if not quest:
                await ctx.followup.send(
                    "No se encontró esa misión o no te pertenece.", ephemeral=True
                )
                return

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
                        description=f"**Jugador:** {player}\n**Misión:** {quest[2]}\n**Recompensa:** {quest[3]}\n\n[Enlace al último mensaje]({last_message_link})",
                        color=discord.Color.orange(),
                    )
                    embed.set_footer(text=f"Quest ID: {quest_id}")
                    message = await channel.send(embed=embed)
                    await message.add_reaction("✅")  # Checkmark reaction
                    await message.add_reaction("❌")  # Cross reaction

                    # Mark quest as completed in database
                    self.mark_quest_as_completed(
                        quest_id, str(ctx.user.id), str(message.id)
                    )

                await ctx.followup.send(
                    "Misión enviada para aprobación.", ephemeral=True
                )
                logger.info(f"Quest {quest_id} completed by {player}: {quest[2]}")
            except Exception as e:
                logger.error(f"Error sending completion notification: {e}")
                await ctx.followup.send(
                    "Error al enviar la notificación de misión completada.",
                    ephemeral=True,
                )

        except Exception as e:
            logger.error(f"Error in handle_complete_command: {e}")
            await ctx.followup.send("Error al completar la misión.", ephemeral=True)

    async def handle_abandon_command(self, ctx, misión: str):
        """Handle the quest abandonment command."""
        try:
            await ctx.defer()

            player = ctx.user.name

            # Extract quest ID from the mission string (format: "ID: Description")
            try:
                quest_id = int(misión.split(":")[0])
            except (ValueError, IndexError):
                await ctx.followup.send(
                    "Formato de misión inválido. Usa el autocompletado para seleccionar una misión.",
                    ephemeral=True,
                )
                return

            # Verify the quest belongs to the user and can be abandoned
            quest = self.get_quest_by_id_and_player(quest_id, player)
            if not quest:
                await ctx.followup.send(
                    "No se encontró esa misión o no te pertenece.", ephemeral=True
                )
                return

            quest_status = quest[4] if len(quest) > 4 else "active"
            if quest_status in ["completed", "approved"]:
                await ctx.followup.send(
                    "No puedes abandonar una misión que ya has completado.",
                    ephemeral=True,
                )
                return

            # Abandon the quest
            success = self.abandon_quest(quest_id, player)
            if success:
                import discord

                embed = discord.Embed(
                    title="🏳️ Misión abandonada",
                    description=f"Has abandonado la misión: **{quest[2]}**",
                    color=discord.Color.orange(),
                )
                embed.set_footer(
                    text="Puedes solicitar nuevas misiones cuando quieras."
                )

                await ctx.followup.send(embed=embed, ephemeral=True)
                logger.info(f"Quest {quest_id} abandoned by {player}: {quest[2]}")
            else:
                await ctx.followup.send(
                    "Error al abandonar la misión. Inténtalo de nuevo.", ephemeral=True
                )

        except Exception as e:
            logger.error(f"Error in handle_abandon_command: {e}")
            await ctx.followup.send("Error al abandonar la misión.", ephemeral=True)

    def get_quest_options_for_player(self, player: str) -> List[str]:
        """Get quest options for autocomplete."""
        try:
            records = self.get_user_active_quests(player)
            return [f"{record[0]}: {record[2]}" for record in records if record[2]]
        except Exception as e:
            logger.error(f"Error getting quest options: {e}")
            return []
