"""
Main RingoBot class that manages the Discord bot and its modules.
"""

import discord
import logging
import asyncio
from datetime import datetime

from utils.config import config
from modules.replies import RepliesModule
from modules.dice import DiceModule
from modules.music import MusicModule
from modules.discape import DiscapeModule
from modules.quests import QuestsModule
from modules.wisdom import WisdomModule, _normalize, _WISDOM_TRIGGER
from modules.characters import CharactersModule
from modules.combat import CombatModule

logger = logging.getLogger(__name__)


class CombatView(discord.ui.View):
    """Discord UI view for combat actions."""
    
    def __init__(self, combat_module, channel_id: int):
        super().__init__(timeout=300)  # 5 minutes timeout
        self.combat_module = combat_module
        self.channel_id = channel_id

    @discord.ui.button(label="⚔️ Atacar", style=discord.ButtonStyle.danger, emoji="⚔️")
    async def attack_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        """Handle attack button press."""
        combat = self.combat_module.get_combat_session(self.channel_id)
        if not combat or combat.turn_phase != "player":
            await interaction.response.send_message("❌ No es el turno de los jugadores.", ephemeral=True)
            return

        participant = None
        for p in combat.participants:
            if p.discord_id == str(interaction.user.id):
                participant = p
                break

        if not participant:
            await interaction.response.send_message("❌ No estás participando en este combate.", ephemeral=True)
            return

        if not participant.is_alive:
            await interaction.response.send_message("❌ Estás fuera de combate.", ephemeral=True)
            return

        if participant.selected_action:
            await interaction.response.send_message("❌ Ya has seleccionado una acción este turno.", ephemeral=True)
            return

        # Set attack action
        action = {"type": "attack"}
        self.combat_module.set_player_action(self.channel_id, str(interaction.user.id), action)
        
        await interaction.response.send_message("⚔️ Has elegido **Atacar**!", ephemeral=True)
        
        # Check if all players are ready to process turn
        if self.combat_module.all_players_ready(self.channel_id):
            await self._process_turn(interaction)

    @discord.ui.button(label="✨ Técnica", style=discord.ButtonStyle.primary, emoji="✨")
    async def technique_button(self, button: discord.ui.Button, interaction: discord.Interaction):
        """Handle technique button press."""
        combat = self.combat_module.get_combat_session(self.channel_id)
        if not combat or combat.turn_phase != "player":
            await interaction.response.send_message("❌ No es el turno de los jugadores.", ephemeral=True)
            return

        participant = None
        for p in combat.participants:
            if p.discord_id == str(interaction.user.id):
                participant = p
                break

        if not participant:
            await interaction.response.send_message("❌ No estás participando en este combate.", ephemeral=True)
            return

        if not participant.is_alive:
            await interaction.response.send_message("❌ Estás fuera de combate.", ephemeral=True)
            return

        if participant.selected_action:
            await interaction.response.send_message("❌ Ya has seleccionado una acción este turno.", ephemeral=True)
            return

        # Get available techniques
        techniques = self.combat_module.get_available_techniques(str(interaction.user.id))
        if not techniques:
            await interaction.response.send_message("❌ No tienes técnicas disponibles.", ephemeral=True)
            return

        # Create technique selection view
        technique_view = TechniqueSelectionView(self.combat_module, self.channel_id, techniques)
        
        embed = discord.Embed(title="✨ Selecciona una Técnica", color=discord.Color.blue())
        for i, technique in enumerate(techniques[:10]):  # Limit to 10 techniques
            cooldown_text = ""
            if technique.id in participant.technique_cooldowns and participant.technique_cooldowns[technique.id] > 0:
                cooldown_text = f" (⏳ {participant.technique_cooldowns[technique.id]} turnos)"
            
            embed.add_field(
                name=f"{i+1}. {technique.name}{cooldown_text}",
                value=f"{technique.description}\n*Basada en: {technique.associated_stat.capitalize()}* | **Costo:** {technique.cost} turno{'s' if technique.cost != 1 else ''}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, view=technique_view, ephemeral=True)

    async def _process_turn(self, interaction: discord.Interaction):
        """Process the turn when all players are ready."""
        try:
            # Get the channel and send turn results
            channel = interaction.guild.get_channel(self.channel_id)
            if not channel:
                await interaction.followup.send("❌ Error: No se pudo encontrar el canal.", ephemeral=True)
                return

            # Process player turn
            results = self.combat_module.process_player_turn(self.channel_id)
            
            if results:
                result_embed = discord.Embed(
                    title="⚔️ Resultados del Turno de Jugadores",
                    description="\n".join(results),
                    color=discord.Color.green()
                )
                await channel.send(embed=result_embed)

            # Check if combat ended
            combat = self.combat_module.get_combat_session(self.channel_id)
            if not combat or combat.enemy.current_hp <= 0:
                self.combat_module.end_combat(self.channel_id)
                victory_embed = discord.Embed(
                    title="🎉 ¡Victoria!",
                    description=f"¡{combat.enemy.name} ha sido derrotado!",
                    color=discord.Color.gold()
                )
                await channel.send(embed=victory_embed)
                return

            # Process enemy turn with proper error handling
            try:
                await asyncio.sleep(2)  # Brief pause for dramatic effect
                enemy_results = self.combat_module.process_enemy_turn(self.channel_id)
                
                if enemy_results:
                    enemy_embed = discord.Embed(
                        title="👹 Turno del Enemigo",
                        description="\n".join(enemy_results),
                        color=discord.Color.red()
                    )
                    await channel.send(embed=enemy_embed)
            except Exception as e:
                await channel.send(f"❌ Error durante el turno del enemigo: {str(e)}")
                return

            # Check if all players defeated
            combat = self.combat_module.get_combat_session(self.channel_id)
            if combat and not any(p.is_alive for p in combat.participants):
                self.combat_module.end_combat(self.channel_id)
                defeat_embed = discord.Embed(
                    title="💀 Derrota",
                    description="Todos los participantes han caído en combate.",
                    color=discord.Color.dark_red()
                )
                await channel.send(embed=defeat_embed)
                return

            # Update combat embed for next turn
            await self._update_combat_embed(channel, combat)

        except Exception as e:
            channel = interaction.guild.get_channel(self.channel_id)
            if channel:
                await channel.send(f"❌ Error crítico durante el procesamiento del turno: {str(e)}")

    async def _update_combat_embed(self, channel, combat):
        """Update the combat embed with current status."""
        try:
            # First, mark the old message as finished if it exists
            if combat.message_id:
                try:
                    old_message = await channel.fetch_message(combat.message_id)
                    
                    # Get the current embed and modify the phase field
                    old_embed = old_message.embeds[0] if old_message.embeds else None
                    if old_embed:
                        # Create a new embed based on the old one
                        finished_embed = discord.Embed(
                            title=old_embed.title,
                            description=old_embed.description,
                            color=discord.Color.greyple()  # Greyish color for finished turns
                        )
                        
                        # Copy all fields except the last one (Phase)
                        for field in old_embed.fields[:-1]:  # All except the last field
                            finished_embed.add_field(
                                name=field.name,
                                value=field.value,
                                inline=field.inline
                            )
                        
                        # Add the finished phase field
                        finished_embed.add_field(name="📋 Fase", value="⏹️ **Turno finalizado**", inline=False)
                        
                        # Remove the view (disable buttons) and update
                        await old_message.edit(embed=finished_embed, view=None)
                except discord.NotFound:
                    pass  # Message was already deleted
                except Exception as e:
                    # Log the error but continue with creating new message
                    print(f"Error updating old message: {e}")

            # Create the new combat embed
            embed = discord.Embed(
                title=f"⚔️ Combate: {combat.enemy.name}",
                description=combat.enemy.description,
                color=discord.Color.red()
            )

            # Enemy status
            hp_bar = self._create_hp_bar(combat.enemy.current_hp, combat.enemy.max_hp)
            embed.add_field(
                name="👹 Estado del Enemigo",
                value=f"{hp_bar}\n❤️ {combat.enemy.current_hp}/{combat.enemy.max_hp} HP",
                inline=False
            )

            # Player status
            players_status = []
            for participant in combat.participants:
                status_icon = "💀" if not participant.is_alive else "⚔️"
                hp_bar = self._create_hp_bar(participant.stats.current_hp, participant.stats.max_hp) if participant.is_alive else "💀💀💀💀💀"
                status_effects = ""
                if participant.status_effects:
                    effects = [effect.value for effect in participant.status_effects.keys()]
                    status_effects = f" ({', '.join(effects)})"
                
                players_status.append(f"{status_icon} **{participant.character_name}**{status_effects}\n{hp_bar} {participant.stats.current_hp}/{participant.stats.max_hp} HP")

            embed.add_field(
                name="🛡️ Participantes",
                value="\n\n".join(players_status),
                inline=False
            )

            # Turn phase
            embed.add_field(name="📋 Fase", value="🎯 **Turno de los jugadores** - Selecciona tu acción", inline=False)

            # Create new view and send new message
            new_view = CombatView(self.combat_module, self.channel_id)
            message = await channel.send(embed=embed, view=new_view)
            combat.message_id = message.id
            
        except Exception as e:
            await channel.send(f"❌ Error actualizando el embed de combate: {str(e)}")

    def _create_hp_bar(self, current_hp: int, max_hp: int, length: int = 10) -> str:
        """Create a visual HP bar."""
        if max_hp <= 0:
            return "💀" * length
        
        percentage = current_hp / max_hp
        filled_length = int(length * percentage)
        empty_length = length - filled_length
        
        return "🟩" * filled_length + "🟥" * empty_length


class TechniqueSelectionView(discord.ui.View):
    """View for selecting techniques."""
    
    def __init__(self, combat_module, channel_id: int, techniques: list):
        super().__init__(timeout=60)  # 1 minute timeout
        self.combat_module = combat_module
        self.channel_id = channel_id
        self.techniques = techniques
        
        # Add buttons for each technique (up to 5)
        for i, technique in enumerate(techniques[:5]):
            button = discord.ui.Button(
                label=f"{i+1}. {technique.name}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"technique_{technique.id}"
            )
            button.callback = self._make_technique_callback(technique.id)
            self.add_item(button)

    def _make_technique_callback(self, technique_id: int):
        """Create callback for technique button."""
        async def technique_callback(interaction: discord.Interaction):
            combat = self.combat_module.get_combat_session(self.channel_id)
            if not combat or combat.turn_phase != "player":
                await interaction.response.send_message("❌ No es el turno de los jugadores.", ephemeral=True)
                return

            participant = None
            for p in combat.participants:
                if p.discord_id == str(interaction.user.id):
                    participant = p
                    break

            if not participant or not participant.is_alive:
                await interaction.response.send_message("❌ No puedes actuar ahora.", ephemeral=True)
                return

            if participant.selected_action:
                await interaction.response.send_message("❌ Ya has seleccionado una acción este turno.", ephemeral=True)
                return

            # Check cooldown
            if technique_id in participant.technique_cooldowns and participant.technique_cooldowns[technique_id] > 0:
                await interaction.response.send_message(f"❌ Debes esperar {participant.technique_cooldowns[technique_id]} turnos más.", ephemeral=True)
                return

            technique = self.combat_module.get_technique(technique_id)
            if not technique:
                await interaction.response.send_message("❌ Técnica no encontrada.", ephemeral=True)
                return

            # Set technique action
            action = {"type": "technique", "technique_id": technique_id}
            self.combat_module.set_player_action(self.channel_id, str(interaction.user.id), action)
            
            await interaction.response.send_message(f"✨ Has elegido usar **{technique.name}**!", ephemeral=True)
            
            # Check if all players are ready
            if self.combat_module.all_players_ready(self.channel_id):
                # Create a CombatView instance to use its turn processing
                combat_view = CombatView(self.combat_module, self.channel_id)
                await combat_view._process_turn(interaction)

        return technique_callback


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
        self.combat_module = CombatModule()

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
            "recompensa",
            description="Recompensa de la misión. Recuerda escribir «PC» para otorgar pucos (ej.: 10 PC)",
            required=True,
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
            autocomplete=discord.utils.basic_autocomplete(misiones),
            required=True,
        )
        async def abandonar(ctx: discord.ApplicationContext, misión: str):
            """Abandona una misión."""
            await self.quests_module.handle_abandon_command(ctx, misión)

        # Character command group
        character = self.bot.create_group(
            "personaje", "Comandos para gestión de personajes y PC"
        )

        @character.command(name="ver", description="Ve la información de tu personaje.")
        async def ver(ctx: discord.ApplicationContext):
            """Ve la información de tu personaje."""
            await self._handle_view_character(ctx)

        @character.command(
            name="actualizar-imagen", description="Actualiza la imagen de tu personaje."
        )
        @discord.option(
            "imagen",
            description="URL de la nueva imagen para tu personaje.",
            required=True,
        )
        async def actualizar_imagen(ctx: discord.ApplicationContext, imagen: str):
            """Actualiza la imagen de tu personaje."""
            await self._handle_update_character_picture(ctx, imagen)

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

        @admin.command(
            name="registrar-personaje",
            description="[ADMIN] Registrar un personaje para un usuario.",
        )
        @discord.option(
            "usuario",
            description="Usuario para el que registrar el personaje.",
            required=True,
        )
        @discord.option("nombre", description="Nombre del personaje.", required=True)
        @discord.option(
            "imagen",
            description="URL de imagen personalizada para el personaje.",
            required=False,
        )
        async def registrar_personaje(
            ctx: discord.ApplicationContext,
            usuario: discord.Member,
            nombre: str,
            imagen: str = None,
        ):
            """[ADMIN] Registrar un personaje para un usuario."""
            await self._handle_admin_register_character(ctx, usuario, nombre, imagen)

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

        @admin.command(
            name="cambiar-nombre",
            description="[ADMIN] Cambiar el nombre de un personaje.",
        )
        @discord.option(
            "usuario", description="Usuario cuyo personaje modificar.", required=True
        )
        @discord.option(
            "nuevo_nombre", description="Nuevo nombre para el personaje.", required=True
        )
        async def cambiar_nombre(
            ctx: discord.ApplicationContext, usuario: discord.Member, nuevo_nombre: str
        ):
            """[ADMIN] Cambiar el nombre de un personaje."""
            await self._handle_change_character_name(ctx, usuario, nuevo_nombre)

        @admin.command(
            name="cambiar-imagen",
            description="[ADMIN] Cambiar la imagen de un personaje.",
        )
        @discord.option(
            "usuario", description="Usuario cuyo personaje modificar.", required=True
        )
        @discord.option(
            "nueva_imagen",
            description="Nueva URL de imagen para el personaje.",
            required=True,
        )
        async def cambiar_imagen(
            ctx: discord.ApplicationContext, usuario: discord.Member, nueva_imagen: str
        ):
            """[ADMIN] Cambiar la imagen de un personaje."""
            await self._handle_change_character_picture(ctx, usuario, nueva_imagen)

        @admin.command(
            name="modificar-personaje",
            description="[ADMIN] Modificar nombre e imagen de un personaje.",
        )
        @discord.option(
            "usuario", description="Usuario cuyo personaje modificar.", required=True
        )
        @discord.option(
            "nuevo_nombre",
            description="Nuevo nombre para el personaje.",
            required=False,
        )
        @discord.option(
            "nueva_imagen",
            description="Nueva URL de imagen para el personaje.",
            required=False,
        )
        async def modificar_personaje(
            ctx: discord.ApplicationContext,
            usuario: discord.Member,
            nuevo_nombre: str = None,
            nueva_imagen: str = None,
        ):
            """[ADMIN] Modificar nombre e imagen de un personaje."""
            await self._handle_modify_character(
                ctx, usuario, nuevo_nombre, nueva_imagen
            )

        # Admin enemy management commands
        @admin.command(name="crear_enemigo", description="Crear un nuevo enemigo")
        @discord.option("nombre", description="Nombre del enemigo", required=True)
        @discord.option("descripcion", description="Descripción del enemigo", required=True)
        @discord.option("hp", description="Puntos de vida máximos", required=True)
        @discord.option("fuerza", description="Modificador de fuerza", required=False, default=0)
        @discord.option("aguante", description="Modificador de aguante", required=False, default=0)
        @discord.option("agilidad", description="Modificador de agilidad", required=False, default=0)
        @discord.option("encanto", description="Modificador de encanto", required=False, default=0)
        @discord.option("conocimiento", description="Modificador de conocimiento", required=False, default=0)
        async def crear_enemigo(ctx: discord.ApplicationContext, nombre: str, descripcion: str, hp: int, 
                               fuerza: int = 0, aguante: int = 0, agilidad: int = 0, encanto: int = 0, conocimiento: int = 0):
            """Crear un nuevo enemigo."""
            # Check if user is admin
            if not any(role.name in config.ADMIN_ROLES for role in ctx.author.roles):
                await ctx.respond("❌ Solo los administradores pueden crear enemigos.", ephemeral=True)
                return

            enemy_id = self.combat_module.create_enemy(
                nombre, descripcion, hp, fuerza, aguante, agilidad, encanto, conocimiento, created_by=str(ctx.author.id)
            )
            
            if enemy_id:
                await ctx.respond(f"✅ Enemigo **{nombre}** creado con ID {enemy_id}.")
            else:
                await ctx.respond("❌ Error al crear enemigo.", ephemeral=True)

        @admin.command(name="listar_enemigos", description="Listar todos los enemigos")
        async def listar_enemigos(ctx: discord.ApplicationContext):
            """Listar enemigos."""
            # Check if user is admin
            if not any(role.name in config.ADMIN_ROLES for role in ctx.author.roles):
                await ctx.respond("❌ Solo los administradores pueden listar enemigos.", ephemeral=True)
                return

            enemies = self.combat_module.list_enemies()
            
            if not enemies:
                await ctx.respond("No hay enemigos registrados.", ephemeral=True)
                return

            embed = discord.Embed(title="👹 Lista de Enemigos", color=discord.Color.dark_red())
            
            for enemy_id, name, description, max_hp in enemies:
                embed.add_field(
                    name=f"ID {enemy_id}: {name}",
                    value=f"{description}\n❤️ HP: {max_hp}",
                    inline=False
                )

            await ctx.respond(embed=embed)

        @admin.command(name="eliminar_enemigo", description="Eliminar un enemigo")
        @discord.option("enemigo_id", description="ID del enemigo a eliminar", required=True)
        async def eliminar_enemigo(ctx: discord.ApplicationContext, enemigo_id: int):
            """Eliminar un enemigo."""
            # Check if user is admin
            if not any(role.name in config.ADMIN_ROLES for role in ctx.author.roles):
                await ctx.respond("❌ Solo los administradores pueden eliminar enemigos.", ephemeral=True)
                return

            success = self.combat_module.delete_enemy(enemigo_id)
            
            if success:
                await ctx.respond(f"✅ Enemigo con ID {enemigo_id} eliminado.")
            else:
                await ctx.respond("❌ Error al eliminar enemigo o enemigo no encontrado.", ephemeral=True)

        # Combat command group
        combat = self.bot.create_group("combate", "Comandos para el sistema de combate RPG")

        @combat.command(name="iniciar", description="Inicia un combate contra un enemigo")
        @discord.option("enemigo_id", description="ID del enemigo a enfrentar", required=True)
        @discord.option("participantes", description="Menciona a los participantes (@usuario1 @usuario2)", required=True)
        async def iniciar_combate(ctx: discord.ApplicationContext, enemigo_id: int, participantes: str):
            """Inicia un combate."""
            # Check if user is admin
            if not any(role.name in config.ADMIN_ROLES for role in ctx.author.roles):
                await ctx.respond("❌ Solo los administradores pueden iniciar combates.", ephemeral=True)
                return

            # Parse participants from mentions
            participant_ids = []
            character_names = {}
            
            # Extract user IDs from mention strings like <@123456789>
            import re
            mention_pattern = r'<@!?(\d+)>'
            user_ids = re.findall(mention_pattern, participantes)
            
            # If no mentions found, try to parse the author as single participant
            if not user_ids:
                user_ids = [str(ctx.author.id)]
            
            for user_id_str in user_ids:
                try:
                    user = await self.bot.fetch_user(int(user_id_str))
                    character = self.characters_module.get_character(user_id_str)
                    if character:
                        participant_ids.append(user_id_str)
                        character_names[user_id_str] = character[2]  # character_name
                    else:
                        await ctx.respond(f"❌ {user.display_name} no tiene un personaje registrado.", ephemeral=True)
                        return
                except (discord.NotFound, discord.HTTPException):
                    await ctx.respond(f"❌ No se pudo encontrar el usuario con ID {user_id_str}.", ephemeral=True)
                    return

            if not participant_ids:
                await ctx.respond("❌ No se encontraron participantes válidos.", ephemeral=True)
                return

            # Start combat
            success = self.combat_module.start_combat(ctx.channel.id, enemigo_id, participant_ids, character_names)
            if success:
                await self._send_combat_embed(ctx)
            else:
                await ctx.respond("❌ No se pudo iniciar el combate. Verifica que el enemigo existe y no hay otro combate activo.", ephemeral=True)

        @combat.command(name="terminar", description="Termina el combate actual en este canal")
        async def terminar_combate(ctx: discord.ApplicationContext):
            """Termina un combate."""
            # Check if user is admin
            if not any(role.name in config.ADMIN_ROLES for role in ctx.author.roles):
                await ctx.respond("❌ Solo los administradores pueden terminar combates.", ephemeral=True)
                return

            success = self.combat_module.end_combat(ctx.channel.id)
            if success:
                await ctx.respond("⚔️ Combate terminado.")
            else:
                await ctx.respond("❌ No hay combate activo en este canal.", ephemeral=True)

        @combat.command(name="estado", description="Muestra el estado actual del combate")
        async def estado_combate(ctx: discord.ApplicationContext):
            """Muestra el estado del combate."""
            combat = self.combat_module.get_combat_session(ctx.channel.id)
            if not combat:
                await ctx.respond("❌ No hay combate activo en este canal.", ephemeral=True)
                return

            await self._send_combat_embed(ctx)

        # Character combat stats commands
        stats = self.bot.create_group("stats", "Comandos para estadísticas de combate")

        @stats.command(name="ver", description="Ver las estadísticas de combate de un personaje")
        @discord.option("usuario", description="Usuario del personaje (opcional)", required=False)
        async def ver_stats(ctx: discord.ApplicationContext, usuario: discord.Member = None):
            """Ver estadísticas de combate."""
            target_user = usuario if usuario else ctx.author
            
            character = self.characters_module.get_character(str(target_user.id))
            if not character:
                await ctx.respond(f"❌ {'Ese usuario' if usuario else 'Tú'} no {'tiene' if usuario else 'tienes'} un personaje registrado.", ephemeral=True)
                return

            stats = self.combat_module.get_character_combat_stats(str(target_user.id))
            if not stats:
                await ctx.respond("❌ Error al obtener estadísticas.", ephemeral=True)
                return

            equipment_bonuses = self.combat_module.get_equipment_bonuses(str(target_user.id))
            
            embed = discord.Embed(
                title=f"⚔️ Estadísticas de {character[2]}",
                color=discord.Color.red()
            )

            embed.add_field(
                name="💪 Fuerza", 
                value=f"{stats.fuerza} + {equipment_bonuses.get('fuerza', 0)} = {stats.fuerza + equipment_bonuses.get('fuerza', 0)}", 
                inline=True
            )
            embed.add_field(
                name="🛡️ Aguante", 
                value=f"{stats.aguante} + {equipment_bonuses.get('aguante', 0)} = {stats.aguante + equipment_bonuses.get('aguante', 0)}", 
                inline=True
            )
            embed.add_field(
                name="💨 Agilidad", 
                value=f"{stats.agilidad} + {equipment_bonuses.get('agilidad', 0)} = {stats.agilidad + equipment_bonuses.get('agilidad', 0)}", 
                inline=True
            )
            embed.add_field(
                name="💫 Encanto", 
                value=f"{stats.encanto} + {equipment_bonuses.get('encanto', 0)} = {stats.encanto + equipment_bonuses.get('encanto', 0)}", 
                inline=True
            )
            embed.add_field(
                name="🧠 Conocimiento", 
                value=f"{stats.conocimiento} + {equipment_bonuses.get('conocimiento', 0)} = {stats.conocimiento + equipment_bonuses.get('conocimiento', 0)}", 
                inline=True
            )
            embed.add_field(
                name="❤️ Vida", 
                value=f"{stats.max_hp + equipment_bonuses.get('max_hp', 0)}", 
                inline=True
            )

            if stats.equipped_weapon or stats.equipped_armor:
                equipment_text = []
                if stats.equipped_weapon:
                    equipment_text.append(f"🗡️ **Arma:** {stats.equipped_weapon}")
                if stats.equipped_armor:
                    equipment_text.append(f"🛡️ **Armadura:** {stats.equipped_armor}")
                embed.add_field(name="🎒 Equipamiento", value="\n".join(equipment_text), inline=False)

            await ctx.respond(embed=embed)

        @stats.command(name="modificar", description="Modificar estadísticas de combate (Solo admins)")
        @discord.option("usuario", description="Usuario del personaje", required=True)
        @discord.option("stat", description="Estadística a modificar", choices=["fuerza", "aguante", "agilidad", "encanto", "conocimiento", "max_hp"], required=True)
        @discord.option("valor", description="Nuevo valor", required=True)
        async def modificar_stats(ctx: discord.ApplicationContext, usuario: discord.Member, stat: str, valor: int):
            """Modificar estadísticas de combate."""
            # Check if user is admin
            if not any(role.name in config.ADMIN_ROLES for role in ctx.author.roles):
                await ctx.respond("❌ Solo los administradores pueden modificar estadísticas.", ephemeral=True)
                return

            character = self.characters_module.get_character(str(usuario.id))
            if not character:
                await ctx.respond("❌ Ese usuario no tiene un personaje registrado.", ephemeral=True)
                return

            # Update stats
            # max_hp is a column of its own; the five attributes are stored as modifiers.
            update_data = {stat if stat == "max_hp" else f"{stat}_modifier": valor}
            success = self.combat_module.update_combat_stats(str(usuario.id), **update_data)
            
            if success:
                await ctx.respond(f"✅ {stat.capitalize()} de {character[2]} actualizada a {valor}.")
            else:
                await ctx.respond("❌ Error al actualizar estadísticas.", ephemeral=True)

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
                title="✅ Carné de residente otorgado",
                description=f"**{nombre}** acaba de obtener su carné.",
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

    async def _handle_admin_register_character(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member,
        nombre: str,
        imagen: str = None,
    ):
        """Handle character registration by admin."""
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
        guild_id = str(ctx.guild.id) if ctx.guild else None

        # Check if character already exists
        existing_character = self.characters_module.get_character(discord_id)
        if existing_character:
            embed = discord.Embed(
                title="❌ Error",
                description=f"{user.mention} ya tiene un personaje registrado: **{existing_character[2]}**",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        # Register new character
        if self.characters_module.register_character(
            discord_id, nombre, guild_id, imagen
        ):
            embed = discord.Embed(
                title="✅ Carné de residente otorgado",
                description=f"**{nombre}** ha sido registrado para {user.mention}.",
                color=discord.Color.green(),
            )
            if imagen:
                embed.add_field(
                    name="Imagen personalizada", value="✅ Configurada", inline=True
                )
            embed.set_footer(
                text="El usuario puede usar /personaje ver para ver su información."
            )
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Hubo un error al registrar el personaje. Inténtalo de nuevo.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)

    async def _handle_view_character(self, ctx: discord.ApplicationContext):
        """Handle viewing character information."""
        discord_id = str(ctx.author.id)
        character = self.characters_module.get_character(discord_id)

        if not character:
            embed = discord.Embed(
                title="❌ Personaje no encontrado",
                description="No tienes un personaje registrado. Contacta con un administrador para que te registre.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)
            return

        _, _, name, points, _, picture_url, created_at, updated_at = character

        embed = discord.Embed(
            title="Carné de residente de Teséia", color=discord.Color.blue()
        )
        embed.add_field(name="Nombre", value=name, inline=True)
        embed.add_field(name="PC actuales", value=f"{points} PC", inline=True)
        embed.add_field(
            name="Residente desde",
            value=f"<t:{int(datetime.fromisoformat(created_at).timestamp())}:R>",
            inline=False,
        )

        # Use character's custom picture if available, otherwise use user's avatar
        thumbnail_url = (
            picture_url
            if picture_url
            else (ctx.author.avatar.url if ctx.author.avatar else None)
        )
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        await ctx.respond(embed=embed)

    async def _handle_update_character_picture(
        self, ctx: discord.ApplicationContext, imagen: str
    ):
        """Handle updating character picture."""
        discord_id = str(ctx.author.id)
        character = self.characters_module.get_character(discord_id)

        if not character:
            embed = discord.Embed(
                title="❌ Personaje no encontrado",
                description="No tienes un personaje registrado. Contacta con un administrador para que te registre.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        # Validate URL format (basic check)
        if not imagen.startswith(("http://", "https://")):
            embed = discord.Embed(
                title="❌ URL inválida",
                description="La URL debe comenzar con http:// o https://",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        # Update character picture
        if self.characters_module.update_picture(discord_id, imagen):
            embed = discord.Embed(
                title="✅ Imagen actualizada",
                description="La imagen de tu personaje ha sido actualizada correctamente.",
                color=discord.Color.green(),
            )
            embed.set_thumbnail(url=imagen)
            embed.set_footer(text="Usa /personaje ver para ver tu carné actualizado.")
            await ctx.respond(embed=embed, ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Hubo un error al actualizar la imagen. Inténtalo de nuevo.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

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

    async def _handle_change_character_name(
        self, ctx: discord.ApplicationContext, user: discord.Member, nuevo_nombre: str
    ):
        """Handle changing a character's name (admin only)."""
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

        old_name = character[2]

        if self.characters_module.update_character_name(discord_id, nuevo_nombre):
            embed = discord.Embed(
                title="✅ Nombre Actualizado",
                description=f"El personaje de {user.mention} ha sido renombrado.",
                color=discord.Color.green(),
            )
            embed.add_field(name="Nombre anterior", value=old_name, inline=True)
            embed.add_field(name="Nombre nuevo", value=nuevo_nombre, inline=True)
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Hubo un error al cambiar el nombre del personaje.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)

    async def _handle_change_character_picture(
        self, ctx: discord.ApplicationContext, user: discord.Member, nueva_imagen: str
    ):
        """Handle changing a character's picture (admin only)."""
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

        # Validate URL format (basic check)
        if not nueva_imagen.startswith(("http://", "https://")):
            embed = discord.Embed(
                title="❌ URL inválida",
                description="La URL debe comenzar con http:// o https://",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        if self.characters_module.update_picture(discord_id, nueva_imagen):
            embed = discord.Embed(
                title="✅ Imagen Actualizada",
                description=f"La imagen del personaje **{character[2]}** de {user.mention} ha sido actualizada.",
                color=discord.Color.green(),
            )
            embed.set_thumbnail(url=nueva_imagen)
            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Hubo un error al cambiar la imagen del personaje.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)

    async def _handle_modify_character(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member,
        nuevo_nombre: str = None,
        nueva_imagen: str = None,
    ):
        """Handle modifying a character's name and/or picture (admin only)."""
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

        # Validate that at least one parameter is provided
        if not nuevo_nombre and not nueva_imagen:
            embed = discord.Embed(
                title="❌ Error",
                description="Debes proporcionar al menos un nuevo nombre o una nueva imagen.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        # Validate URL format if provided
        if nueva_imagen and not nueva_imagen.startswith(("http://", "https://")):
            embed = discord.Embed(
                title="❌ URL inválida",
                description="La URL debe comenzar con http:// o https://",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        old_name = character[2]

        if self.characters_module.update_character_info(
            discord_id, nuevo_nombre, nueva_imagen
        ):
            embed = discord.Embed(
                title="✅ Personaje Modificado",
                description=f"El personaje de {user.mention} ha sido actualizado.",
                color=discord.Color.green(),
            )

            if nuevo_nombre:
                embed.add_field(name="Nombre anterior", value=old_name, inline=True)
                embed.add_field(name="Nombre nuevo", value=nuevo_nombre, inline=True)

            if nueva_imagen:
                embed.add_field(name="Imagen", value="✅ Actualizada", inline=True)
                embed.set_thumbnail(url=nueva_imagen)

            await ctx.respond(embed=embed)
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Hubo un error al modificar el personaje.",
                color=discord.Color.red(),
            )
            await ctx.respond(embed=embed)

    async def _send_combat_embed(self, ctx: discord.ApplicationContext):
        """Send or update combat embed with action buttons."""
        combat = self.combat_module.get_combat_session(ctx.channel.id)
        if not combat:
            return

        embed = discord.Embed(
            title=f"⚔️ Combate: {combat.enemy.name}",
            description=combat.enemy.description,
            color=discord.Color.red()
        )

        # Enemy status
        hp_bar = self._create_hp_bar(combat.enemy.current_hp, combat.enemy.max_hp)
        embed.add_field(
            name="👹 Estado del Enemigo",
            value=f"{hp_bar}\n❤️ {combat.enemy.current_hp}/{combat.enemy.max_hp} HP",
            inline=False
        )

        # Player status
        players_status = []
        for participant in combat.participants:
            status_icon = "💀" if not participant.is_alive else "⚔️"
            hp_bar = self._create_hp_bar(participant.stats.current_hp, participant.stats.max_hp) if participant.is_alive else "💀💀💀💀💀"
            status_effects = ""
            if participant.status_effects:
                effects = [effect.value for effect in participant.status_effects.keys()]
                status_effects = f" ({', '.join(effects)})"
            
            players_status.append(f"{status_icon} **{participant.character_name}**{status_effects}\n{hp_bar} {participant.stats.current_hp}/{participant.stats.max_hp} HP")

        embed.add_field(
            name="🛡️ Participantes",
            value="\n\n".join(players_status),
            inline=False
        )

        # Turn phase
        phase_text = "🎯 **Turno de los jugadores** - Selecciona tu acción" if combat.turn_phase == "player" else "👹 **Turno del enemigo**"
        embed.add_field(name="📋 Fase", value=phase_text, inline=False)

        # Create action buttons
        view = CombatView(self.combat_module, ctx.channel.id) if combat.turn_phase == "player" else discord.ui.View()

        # Always send a new message instead of editing
        message = await ctx.send(embed=embed, view=view)
        combat.message_id = message.id

    def _create_hp_bar(self, current_hp: int, max_hp: int, length: int = 10) -> str:
        """Create a visual HP bar."""
        if max_hp <= 0:
            return "💀" * length
        
        percentage = current_hp / max_hp
        filled_length = int(length * percentage)
        empty_length = length - filled_length
        
        return "🟩" * filled_length + "🟥" * empty_length

    def run(self):
        """Start the bot."""
        logger.info("Starting RingoBot...")
        self.bot.run(config.TOKEN)
