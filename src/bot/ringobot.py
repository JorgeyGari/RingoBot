"""
Main RingoBot class that manages the Discord bot and its modules.
"""

import discord
import logging
import sys
from typing import Optional, List

from utils.config import config
from modules.replies import RepliesModule
from modules.dice import DiceModule
from modules.music import MusicModule
from modules.discape import DiscapeModule
from modules.quests import QuestsModule

logger = logging.getLogger(__name__)


class RingoBot:
    """Main bot class that orchestrates all modules."""

    def __init__(self):
        """Initialize the bot and its modules."""
        # Validate configuration
        config_errors = config.validate_config()
        if config_errors:
            logger.error("Configuration errors:")
            for error in config_errors:
                logger.error(f"  - {error}")
            sys.exit(1)

        # Set up Discord intents
        intents = discord.Intents.all()

        # Create the bot instance
        self.bot = discord.Bot(debug_guilds=config.DEBUG_GUILDS, intents=intents)

        # Initialize modules
        self.replies_module = RepliesModule()
        self.dice_module = DiceModule()
        self.music_module = MusicModule()
        self.discape_module = DiscapeModule()
        self.quests_module = QuestsModule()

        # Register event handlers
        self._register_events()

        # In-memory cache for hall of fame messages
        self.hall_of_fame_cache = set()

        # Register slash commands
        self._register_commands()

        logger.info("RingoBot initialized successfully")

    def _register_events(self):
        """Register bot event handlers."""

        @self.bot.event
        async def on_ready():
            logger.info(f"¡{self.bot.user} se ha conectado!")

        @self.bot.event
        async def on_message(message: discord.Message):
            if message.author.id == self.bot.user.id:
                return

            logger.info(f"{message.author} en #{message.channel}: {message.content}")

            # Handle private message commands (starting with $)
            if message.content.startswith("$"):
                msg = message.content[1:]
                reply = self.replies_module.handle_message(msg)
                if reply:
                    await message.author.send(reply)
                return

            # Handle regular message replies
            reply = self.replies_module.handle_message(message.content)
            if reply:
                await message.reply(reply, mention_author=True)

        @self.bot.event
        async def on_reaction_add(reaction, user):
            if reaction.emoji == config.STAR_EMOJI and not user.bot:
                if reaction.count >= config.REQUIRED_STARS:
                    channel = self.bot.get_channel(config.HALL_OF_FAME_CHANNEL_ID)
                    message_id = reaction.message.id

                    # Check if message is already in hall of fame using cache
                    if message_id in self.hall_of_fame_cache:
                        return

                    # Send to hall of fame
                    embed = discord.Embed(description=reaction.message.content)
                    embed.set_author(
                        name=reaction.message.author.display_name,
                        icon_url=reaction.message.author.avatar.url,
                    )
                    await channel.send(embed=embed)
                    self.hall_of_fame_cache.add(message_id)

    def _register_commands(self):
        """Register slash commands."""

        # Dice rolling command
        @self.bot.slash_command()
        @discord.option(
            "dados",
            description='Cantidad y tipo de dado a tirar. Por ejemplo, "2d6", "1d20" o "4df".',
        )
        @discord.option(
            "modificador",
            description='Modificador a aplicar a la tirada. Por ejemplo, "+2" o "-1".',
            default=0,
            required=False,
        )
        async def dado(ctx: discord.ApplicationContext, dados: str, modificador: int):
            """Tirar dados."""
            await self.dice_module.handle_roll_command(ctx, dados, modificador)

        # Music command
        @self.bot.slash_command(
            name="ytmusic",
            description="Reproduce música de YouTube en tu canal de voz.",
        )
        @discord.option(
            "link", description="Enlace del video de YouTube.", required=True
        )
        async def ytmusic(ctx: discord.ApplicationContext, link: str):
            """Reproduce música de YouTube en tu canal de voz."""
            await self.music_module.play_youtube_music(ctx, self.bot, link)

        # Escape room command group
        escape = self.bot.create_group(
            "escape", "Comandos para juegos de sala de huida"
        )

        @escape.command(
            name="iniciar", description="Inicia una partida de sala de huida."
        )
        @discord.option(
            "archivo", description="Archivo de sala de huida.", required=True
        )
        async def iniciar(ctx: discord.ApplicationContext, archivo: discord.Attachment):
            """Inicia una partida de sala de huida."""
            await self.discape_module.handle_start_command(ctx, archivo)

        @escape.command(
            name="tirada",
            description="Tira un dado de 20 caras y suma tu bonificación de la característica elegida.",
        )
        @discord.option(
            "característica",
            description="Característica a tirar.",
            choices=["Fuerza", "Resistencia", "Agilidad", "Inteligencia", "Suerte"],
            required=True,
        )
        async def tirada(ctx: discord.ApplicationContext, característica: str):
            """Haz una tirada con una estadística."""
            await self.discape_module.handle_stat_roll_command(ctx, característica)

        @escape.command(name="investigar", description="Investiga en la sala de huida.")
        @discord.option(
            "objetivo",
            description="¿Qué quieres investigar?",
            autocomplete=discord.utils.basic_autocomplete(
                self._get_investigation_options
            ),
            required=True,
        )
        async def investigar(ctx: discord.ApplicationContext, objetivo: str):
            """Investiga en la sala de huida."""
            await self.discape_module.handle_investigate_command(ctx, objetivo)

        @escape.command(
            name="objetos", description="Muestra los objetos de tu inventario."
        )
        async def objetos(ctx: discord.ApplicationContext):
            """Muestra los objetos de tu inventario."""
            await self.discape_module.handle_inventory_command(ctx)

        @escape.command(name="equipar", description="Equipar un objeto.")
        @discord.option(
            "objeto",
            description="¿Qué objeto quieres equipar?",
            autocomplete=discord.utils.basic_autocomplete(self._get_equipable_items),
            required=True,
        )
        async def equipar(ctx: discord.ApplicationContext, objeto: str):
            """Equipar un objeto."""
            await self.discape_module.handle_equip_command(ctx, objeto)

        @escape.command(name="combinar", description="Combina dos objetos.")
        @discord.option(
            "objeto1",
            description="¿Qué objeto quieres combinar?",
            autocomplete=discord.utils.basic_autocomplete(self._get_equipable_items),
            required=True,
        )
        @discord.option(
            "objeto2",
            description="¿Con qué objeto quieres combinarlo?",
            autocomplete=discord.utils.basic_autocomplete(self._get_equipable_items),
            required=True,
        )
        async def combinar(ctx: discord.ApplicationContext, objeto1: str, objeto2: str):
            """Combina dos objetos."""
            await self.discape_module.handle_combine_command(ctx, objeto1, objeto2)

        @escape.command(
            name="unirse", description="Unirse a una partida de sala de huida."
        )
        async def unirse(ctx: discord.ApplicationContext):
            """Unirse a una partida de sala de huida."""
            await self.discape_module.handle_join_command(ctx)

        # Mission/Quest command group
        mission = self.bot.create_group("misión", "Comandos para misiones de rol")

        @mission.command(name="solicitar", description="Solicita una misión.")
        async def solicitar(ctx: discord.ApplicationContext):
            """Solicita una misión."""
            await self.quests_module.handle_request_command(ctx)

        @mission.command(name="crear", description="Crea una misión.")
        @discord.option(
            "jugador",
            description="Jugador al que asignar la misión.",
            autocomplete=discord.utils.basic_autocomplete(
                self._get_pending_quest_users
            ),
            required=True,
        )
        @discord.option(
            "descripción", description="Descripción de la misión.", required=True
        )
        @discord.option(
            "recompensa", description="Recompensa de la misión.", required=True
        )
        async def crear(
            ctx: discord.ApplicationContext,
            jugador: str,
            descripción: str,
            recompensa: str,
        ):
            """Crea una misión."""
            await self.quests_module.handle_create_command(
                ctx, jugador, descripción, recompensa
            )

        @mission.command(name="completar", description="Completa una misión.")
        @discord.option(
            "misión",
            description="Misión que has completado.",
            autocomplete=discord.utils.basic_autocomplete(self._get_quest_options),
            required=True,
        )
        async def completar(ctx: discord.ApplicationContext, misión: str):
            """Completa una misión."""
            await self.quests_module.handle_complete_command(ctx, misión)

    def _get_investigation_options(self, ctx: discord.AutocompleteContext) -> List[str]:
        """Get autocomplete options for investigation command."""
        try:
            player_name = ctx.interaction.user.name
            return self.discape_module.get_investigation_options(player_name)
        except Exception as e:
            logger.error(f"Error getting investigation options: {e}")
            return []

    def _get_equipable_items(self, ctx: discord.AutocompleteContext) -> List[str]:
        """Get autocomplete options for equipable items."""
        try:
            player_name = ctx.interaction.user.name
            return self.discape_module.get_equipable_items_for_player(player_name)
        except Exception as e:
            logger.error(f"Error getting equipable items: {e}")
            return []

    def _get_quest_options(self, ctx: discord.AutocompleteContext) -> List[str]:
        """Get autocomplete options for active quests."""
        try:
            player_name = ctx.interaction.user.name
            return self.quests_module.get_quest_options_for_player(player_name)
        except Exception as e:
            logger.error(f"Error getting quest options: {e}")
            return []

    def _get_pending_quest_users(self, ctx: discord.AutocompleteContext) -> List[str]:
        """Get autocomplete options for users with pending quest requests."""
        try:
            return self.quests_module.get_users_with_pending_requests()
        except Exception as e:
            logger.error(f"Error getting pending quest users: {e}")
            return []

    def run(self):
        """Start the bot."""
        logger.info("Starting RingoBot...")
        try:
            self.bot.run(config.TOKEN)
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            sys.exit(1)
