"""
Main RingoBot class that manages the Discord bot and its modules.
"""

import discord
import logging
from datetime import datetime

from utils.config import config
from modules.replies import RepliesModule
from modules.dice import DiceModule
from modules.music import MusicModule
from modules.discape import DiscapeModule
from modules.quests import QuestsModule
from modules.wisdom import WisdomModule, _normalize, _WISDOM_TRIGGER
from modules.characters import CharactersModule

logger = logging.getLogger(__name__)


class RingoBot:
    """Main bot class that orchestrates all modules."""

    def __init__(self):
        """Initialize the bot and its modules."""
        # Validate configuration
        config.validate_config()

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
        self.wisdom_module = WisdomModule(config.WISDOMS_FILE)
        self.characters_module = CharactersModule()

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
            await self.bot.sync_commands()
            logger.info("Commands synced with Discord")

        @self.bot.event
        async def on_message(message: discord.Message):
            if message.author.id == self.bot.user.id:
                return

            logger.info(f"{message.author} en #{message.channel}: {message.content}")

            # Handle private message commands (starting with $)
            if message.content.startswith("$"):
                msg = message.content[1:]
                reply = self.replies_module.handle_message(msg)
                if reply and not reply.startswith("emoji_react:"):
                    await message.author.send(reply)
                return

            # Handle wisdom message trigger
            if _WISDOM_TRIGGER.search(_normalize(message.content)):
                await self.wisdom_module.handle_wisdom_message(message)
                return

            # Handle regular message replies
            reply = self.replies_module.handle_message(message.content)
            if reply:
                # Check if reply is an emoji reaction
                if reply.startswith("emoji_react:"):
                    emoji_name = reply[12:]  # Remove "emoji_react:" prefix
                    emoji_map = {"waving_hand": "👋"}
                    emoji = emoji_map.get(emoji_name, emoji_name)
                    await message.add_reaction(emoji)
                else:
                    await message.reply(reply, mention_author=True)

        @self.bot.event
        async def on_reaction_add(reaction, user):
            # Handle hall of fame reactions
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

            # Handle quest approval/rejection reactions
            if (
                not user.bot
                and reaction.message.channel.id == config.COMPLETED_QUESTS_CHANNEL_ID
            ):
                # Check if user has admin permissions
                member = reaction.message.guild.get_member(user.id)
                if member and member.guild_permissions.administrator:
                    message_id = str(reaction.message.id)
                    user_id = str(user.id)

                    if reaction.emoji == "✅":
                        # Quest approval
                        success = await self.quests_module.handle_quest_approval(
                            self.bot, message_id, user_id
                        )
                        if success:
                            try:
                                # Update the embed to show approval
                                embed = reaction.message.embeds[0]
                                embed.color = discord.Color.green()
                                embed.title = "✅ Misión cumplida"
                                embed.set_footer(
                                    text=f"Comprobada por {user.display_name}"
                                )
                                await reaction.message.edit(embed=embed)
                                await reaction.message.clear_reactions()
                            except Exception as e:
                                logger.error(f"Error updating approval message: {e}")

                    elif reaction.emoji == "❌":
                        # Quest rejection
                        success = await self.quests_module.handle_quest_rejection(
                            self.bot, message_id, user_id
                        )
                        if success:
                            try:
                                # Update the embed to show rejection
                                embed = reaction.message.embeds[0]
                                embed.color = discord.Color.red()
                                embed.title = "❌ Misión no cumplida"
                                embed.set_footer(
                                    text=f"Comprobada por {user.display_name}"
                                )
                                await reaction.message.edit(embed=embed)
                                await reaction.message.clear_reactions()
                            except Exception as e:
                                logger.error(f"Error updating rejection message: {e}")

    def _register_commands(self):
        """Register slash commands."""

        # Autocomplete callbacks. The modules already return [] on their own
        # errors, so these only need to pull the player name off the context.
        investigables = lambda ctx: self.discape_module.get_investigation_options(
            ctx.interaction.user.name
        )
        equipables = lambda ctx: self.discape_module.get_equipable_items_for_player(
            ctx.interaction.user.name
        )
        misiones = lambda ctx: self.quests_module.get_quest_options_for_player(
            ctx.interaction.user.name
        )
        solicitantes = lambda ctx: self.quests_module.get_users_with_pending_requests()

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

        # Wisdom command group
        sabiduria = self.bot.create_group("sabiduria", "Comandos para gestionar la sabiduría")

        @sabiduria.command(name="aleatoria", description="Obtén una sabiduría aleatoria")
        async def sabiduria_aleatoria(ctx: discord.ApplicationContext):
            """Pídele a RingoBot que comparta su infinita sabiduría."""
            await self.wisdom_module.handle_wisdom_command(ctx, None)

        @sabiduria.command(name="nueva", description="Registra una nueva sabiduría")
        @discord.option(
            "texto",
            description="La sabiduría a registrar.",
            required=True,
        )
        async def sabiduria_nueva(ctx: discord.ApplicationContext, texto: str):
            """Registra una nueva sabiduría."""
            await self.wisdom_module.handle_wisdom_command(ctx, texto)

        @sabiduria.command(name="eliminar", description="Elimina una de tus sabidurías")
        async def sabiduria_eliminar(ctx: discord.ApplicationContext):
            """Elimina una de tus sabidurías."""
            await self.wisdom_module.handle_delete_command(ctx)

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
            autocomplete=discord.utils.basic_autocomplete(investigables),
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
            autocomplete=discord.utils.basic_autocomplete(equipables),
            required=True,
        )
        async def equipar(ctx: discord.ApplicationContext, objeto: str):
            """Equipar un objeto."""
            await self.discape_module.handle_equip_command(ctx, objeto)

        @escape.command(name="combinar", description="Combina dos objetos.")
        @discord.option(
            "objeto1",
            description="¿Qué objeto quieres combinar?",
            autocomplete=discord.utils.basic_autocomplete(equipables),
            required=True,
        )
        @discord.option(
            "objeto2",
            description="¿Con qué objeto quieres combinarlo?",
            autocomplete=discord.utils.basic_autocomplete(equipables),
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
        mission = self.bot.create_group("mision", "Comandos para misiones de rol")

        @mission.command(name="solicitar", description="Solicita una misión.")
        async def solicitar(ctx: discord.ApplicationContext):
            """Solicita una misión."""
            await self.quests_module.handle_request_command(ctx)

        @mission.command(name="crear", description="Crea una misión.")
        @discord.option(
            "jugador",
            description="Jugador al que asignar la misión.",
            autocomplete=discord.utils.basic_autocomplete(solicitantes),
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
            autocomplete=discord.utils.basic_autocomplete(misiones),
            required=True,
        )
        async def completar(ctx: discord.ApplicationContext, misión: str):
            """Completa una misión."""
            await self.quests_module.handle_complete_command(ctx, misión)

        @mission.command(name="abandonar", description="Abandona una misión asignada.")
        @discord.option(
            "misión",
            description="Misión que quieres abandonar.",
            autocomplete=discord.utils.basic_autocomplete(self._get_quest_options),
            required=True,
        )
        async def abandonar(ctx: discord.ApplicationContext, misión: str):
            """Abandona una misión."""
            await self.quests_module.handle_abandon_command(ctx, misión)

        # Character command group
        character = self.bot.create_group(
            "personaje", "Comandos para gestión de personajes y PC"
        )

        @character.command(
            name="registrar", description="Registra tu personaje en el sistema."
        )
        @discord.option("nombre", description="Nombre de tu personaje.", required=True)
        async def registrar(ctx: discord.ApplicationContext, nombre: str):
            """Registra un nuevo personaje."""
            await self._handle_register_character(ctx, nombre)

        @character.command(name="ver", description="Ve la información de tu personaje.")
        async def ver(ctx: discord.ApplicationContext):
            """Ve la información de tu personaje."""
            await self._handle_view_character(ctx)

        @character.command(
            name="ranking", description="Ve el ranking de personajes por PC."
        )
        @discord.option(
            "límite",
            description="Número de personajes a mostrar (por defecto: 10).",
            required=False,
            default=10,
        )
        async def ranking(ctx: discord.ApplicationContext, límite: int):
            """Ve el ranking de personajes por PC."""
            await self._handle_leaderboard(ctx, límite)

        @character.command(
            name="historial", description="Ve el historial de cambios de PC."
        )
        async def historial(ctx: discord.ApplicationContext):
            """Ve el historial de cambios de PC."""
            await self._handle_point_history(ctx)

        # Admin commands for managing PC
        admin = self.bot.create_group("admin", "Comandos administrativos")

        @admin.command(name="dar-pc", description="[ADMIN] Dar PC a un personaje.")
        @discord.option("usuario", description="Usuario al que dar PC.", required=True)
        @discord.option("cantidad", description="Cantidad de PC a dar.", required=True)
        @discord.option(
            "razón", description="Razón para dar los PC.", required=False, default=""
        )
        async def dar_pc(
            ctx: discord.ApplicationContext,
            usuario: discord.Member,
            cantidad: int,
            razón: str,
        ):
            """[ADMIN] Dar PC a un personaje."""
            await self._handle_give_points(ctx, usuario, cantidad, razón)

        @admin.command(
            name="quitar-pc", description="[ADMIN] Quitar PC a un personaje."
        )
        @discord.option(
            "usuario", description="Usuario al que quitar PC.", required=True
        )
        @discord.option(
            "cantidad", description="Cantidad de PC a quitar.", required=True
        )
        @discord.option(
            "razón", description="Razón para quitar los PC.", required=False, default=""
        )
        async def quitar_pc(
            ctx: discord.ApplicationContext,
            usuario: discord.Member,
            cantidad: int,
            razón: str,
        ):
            """[ADMIN] Quitar PC a un personaje."""
            await self._handle_remove_points(ctx, usuario, cantidad, razón)

        @admin.command(
            name="borrar-personaje", description="[ADMIN] Borrar un personaje."
        )
        @discord.option(
            "usuario", description="Usuario cuyo personaje borrar.", required=True
        )
        async def borrar_personaje(
            ctx: discord.ApplicationContext, usuario: discord.Member
        ):
            """[ADMIN] Borrar un personaje."""
            await self._handle_delete_character(ctx, usuario)

    async def _handle_register_character(
        self, ctx: discord.ApplicationContext, nombre: str
    ):
        """Handle character registration."""
        discord_id = str(ctx.author.id)
        guild_id = str(ctx.guild.id) if ctx.guild else None

        # Check if character already exists
        existing_character = self.characters_module.get_character(discord_id)
        if existing_character:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Ya tienes un personaje registrado: **{existing_character[2]}**",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        # Register new character
        if self.characters_module.register_character(discord_id, nombre, guild_id):
            embed = discord.Embed(
                title="✅ Personaje Registrado",
                description=f"**{nombre}** ha sido registrado exitosamente con 0 PC.",
                color=discord.Color.green(),
            )
            embed.set_footer(text="Usa /personaje ver para ver tu información.")
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Hubo un error al registrar tu personaje. Inténtalo de nuevo.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)

    async def _handle_view_character(self, ctx: discord.ApplicationContext):
        """Handle viewing character information."""
        discord_id = str(ctx.author.id)
        character = self.characters_module.get_character(discord_id)

        if not character:
            embed = discord.Embed(
                title="❌ Personaje No Encontrado",
                description="No tienes un personaje registrado. Usa `/personaje registrar` para crear uno.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        _, _, name, points, _, created_at, updated_at = character

        embed = discord.Embed(
            title="📋 Información del Personaje", color=discord.Color.blue()
        )
        embed.add_field(name="Nombre", value=name, inline=True)
        embed.add_field(name="PC Actuales", value=f"{points} PC", inline=True)
        embed.add_field(
            name="Registrado",
            value=f"<t:{int(datetime.fromisoformat(created_at).timestamp())}:R>",
            inline=False,
        )
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else None)

        await ctx.respond(embed=embed)

    async def _handle_leaderboard(self, ctx: discord.ApplicationContext, limit: int):
        """Handle leaderboard display."""
        guild_id = str(ctx.guild.id) if ctx.guild else None
        leaderboard = self.characters_module.get_leaderboard(guild_id, min(limit, 20))

        if not leaderboard:
            embed = discord.Embed(
                title="📊 Ranking de PC",
                description="No hay personajes registrados aún.",
                color=discord.Color.orange(),
            )
            await ctx.respond(embed=embed)
            return

        embed = discord.Embed(title="📊 Ranking de PC", color=discord.Color.gold())

        description = ""
        for i, (name, points, discord_id) in enumerate(leaderboard, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            try:
                user = await self.bot.fetch_user(int(discord_id))
                username = user.display_name
            except:
                username = "Usuario desconocido"

            description += f"{medal} **{name}** ({username}) - {points} PC\n"

        embed.description = description
        await ctx.respond(embed=embed)

    async def _handle_point_history(self, ctx: discord.ApplicationContext):
        """Handle point history display."""
        discord_id = str(ctx.author.id)
        character = self.characters_module.get_character(discord_id)

        if not character:
            embed = discord.Embed(
                title="❌ Personaje No Encontrado",
                description="No tienes un personaje registrado.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        history = self.characters_module.get_point_history(discord_id, 10)

        embed = discord.Embed(
            title=f"📈 Historial de PC - {character[2]}", color=discord.Color.purple()
        )

        if not history:
            embed.description = "No hay historial de cambios de PC."
        else:
            description = ""
            for points_change, reason, admin_id, timestamp in history:
                sign = "+" if points_change > 0 else ""
                date = f"<t:{int(datetime.fromisoformat(timestamp).timestamp())}:R>"
                admin_text = f" (por <@{admin_id}>)" if admin_id else ""
                reason_text = f" - {reason}" if reason else ""
                description += (
                    f"{sign}{points_change} PC{admin_text}{reason_text} {date}\n"
                )

            embed.description = description

        await ctx.respond(embed=embed)

    async def _handle_give_points(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member,
        amount: int,
        reason: str,
    ):
        """Handle giving points to a character (admin only)."""
        # Check if user has admin permissions
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Sin Permisos",
                description="Solo los administradores pueden usar este comando.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        discord_id = str(user.id)
        character = self.characters_module.get_character(discord_id)

        if not character:
            embed = discord.Embed(
                title="❌ Personaje No Encontrado",
                description=f"{user.mention} no tiene un personaje registrado.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        if amount <= 0:
            embed = discord.Embed(
                title="❌ Error",
                description="La cantidad debe ser mayor a 0.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        admin_id = str(ctx.author.id)
        if self.characters_module.update_points(discord_id, amount, reason, admin_id):
            updated_character = self.characters_module.get_character(discord_id)
            new_points = updated_character[3]

            embed = discord.Embed(
                title="✅ PC Otorgados",
                description=f"Se han dado **{amount} PC** a **{character[2]}** ({user.mention})",
                color=discord.Color.green(),
            )
            embed.add_field(name="PC Totales", value=f"{new_points} PC", inline=True)
            if reason:
                embed.add_field(name="Razón", value=reason, inline=False)

            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Hubo un error al otorgar los PC.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)

    async def _handle_remove_points(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member,
        amount: int,
        reason: str,
    ):
        """Handle removing points from a character (admin only)."""
        # Check if user has admin permissions
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Sin Permisos",
                description="Solo los administradores pueden usar este comando.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        discord_id = str(user.id)
        character = self.characters_module.get_character(discord_id)

        if not character:
            embed = discord.Embed(
                title="❌ Personaje No Encontrado",
                description=f"{user.mention} no tiene un personaje registrado.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        if amount <= 0:
            embed = discord.Embed(
                title="❌ Error",
                description="La cantidad debe ser mayor a 0.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        admin_id = str(ctx.author.id)
        if self.characters_module.update_points(discord_id, -amount, reason, admin_id):
            updated_character = self.characters_module.get_character(discord_id)
            new_points = updated_character[3]

            embed = discord.Embed(
                title="✅ PC Removidos",
                description=f"Se han quitado **{amount} PC** a **{character[2]}** ({user.mention})",
                color=discord.Color.orange(),
            )
            embed.add_field(name="PC Totales", value=f"{new_points} PC", inline=True)
            if reason:
                embed.add_field(name="Razón", value=reason, inline=False)

            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Hubo un error al quitar los PC.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)

    async def _handle_delete_character(
        self, ctx: discord.ApplicationContext, user: discord.Member
    ):
        """Handle deleting a character (admin only)."""
        # Check if user has admin permissions
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Sin Permisos",
                description="Solo los administradores pueden usar este comando.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        discord_id = str(user.id)
        character = self.characters_module.get_character(discord_id)

        if not character:
            embed = discord.Embed(
                title="❌ Personaje No Encontrado",
                description=f"{user.mention} no tiene un personaje registrado.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        if self.characters_module.delete_character(discord_id):
            embed = discord.Embed(
                title="✅ Personaje Eliminado",
                description=f"El personaje **{character[2]}** de {user.mention} ha sido eliminado.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Hubo un error al eliminar el personaje.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)

    def run(self):
        """Start the bot."""
        logger.info("Starting RingoBot...")
        self.bot.run(config.TOKEN)
