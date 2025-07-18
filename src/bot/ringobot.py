"""
Main RingoBot class that manages the Discord bot and its modules.
"""

import discord
import logging
import sys
from typing import Optional

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

    def run(self):
        """Start the bot."""
        logger.info("Starting RingoBot...")
        try:
            self.bot.run(config.TOKEN)
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            sys.exit(1)
