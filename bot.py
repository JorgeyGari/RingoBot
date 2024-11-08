import discord
from discord import option
import os
from dotenv import load_dotenv

import replies
import dice

import discape
import quests

from config import *
import datetime

intents = discord.Intents.all()

load_dotenv()
bot = discord.Bot(debug_guilds=[429400823395647489], intents=intents)
TOKEN = os.getenv("TOKEN")

conn_que = quests.create_connection("quests.db")
quests.create_table(conn_que)


@bot.event
async def on_ready():
    print(f"¡{bot.user} se ha conectado!")


@bot.event
async def on_message(message: discord.Message):
    if message.author.id == bot.user.id:
        return

    else:
        print(f"{message.author} en #{message.channel}: {message.content}")
        if message.content.startswith("$"):
            msg = message.content[1:]
            reply = replies.handler(msg)
            if reply:
                await message.author.send(reply)
        reply = replies.handler(message.content)
        if reply:
            await message.reply(reply, mention_author=True)


@bot.event
async def emoji_reaction(message, emoji):
    try:
        await message.add_reaction(emoji)
    except Exception as e:
        print(e)


@bot.event
async def on_reaction_add(reaction, user):
    if reaction.emoji == STAR_EMOJI and not user.bot:
        if reaction.count >= REQUIRED_STARS:
            channel = bot.get_channel(HALL_OF_FAME_CHANNEL_ID)

            # Make sure the message isn't already in the hall-of-fame channel
            async for message in channel.history(limit=200):
                if message.content == reaction.message.content:
                    return

            # Send the message content to the hall-of-fame channel
            embed = discord.Embed(description=reaction.message.content)
            embed.set_author(
                name=reaction.message.author.display_name,
                icon_url=reaction.message.author.avatar.url,
            )
            await channel.send(embed=embed)


@bot.slash_command()
@option(
    "dados",
    description='Cantidad y tipo de dado a tirar. Por ejemplo, "2d6", "1d20" o "4df".',
)
@option(
    "modificador",
    description='Modificador a aplicar a la tirada. Por ejemplo, "+2" o "-1".',
    default=0,
    required=False,
)
async def dado(ctx: discord.ApplicationContext, dados: str, modificador: int):
    """Tirar dados."""
    if dice.invalid(dados):
        await ctx.respond(dice.invalid(dados), ephemeral=True)
        return
    roll = dice.roll_dice(dados)
    total_roll = dice.total_roll(roll) + modificador
    await ctx.respond(
        f"¡Has tirado {dice.human_read(dados)}!\n"
        f"`{roll}`\n"
        f"**Total:** {total_roll}"
    )


escape = bot.create_group("escape", "Comandos para juegos de sala de huida")
mission = bot.create_group("misión", "Comandos para misiones de rol")


@escape.command(name="iniciar", description="Inicia una partida de sala de huida.")
@option("archivo", description="Archivo de sala de huida.", required=True)
async def iniciar(ctx: discord.ApplicationContext, archivo: discord.Attachment):
    """Inicia una partida de sala de huida."""
    await archivo.save("file.xlsx")
    return await ctx.respond("Archivo cargado.")


@escape.command(
    name="tirada",
    description="Tira un dado de 20 caras y suma tu bonificación de la característica elegida.",
)
@option(
    "característica",
    description="Característica a tirar.",
    choices=["Fuerza", "Resistencia", "Agilidad", "Inteligencia", "Suerte"],
    required=True,
)
async def tirada(ctx: discord.ApplicationContext, característica: str):
    player = ctx.author.name
    """Haz una tirada con una estadística."""
    bonus = discape.get_stat(player, característica)
    roll = dice.roll_dice("1d20")
    roll_sum = dice.total_roll(roll)
    result = int(roll_sum) + int(bonus)
    await ctx.respond(
        f"¡Has usado {característica}!\n" f"`{roll}`\n" f"**Total:** {result}"
    )


async def get_investigation_options(ctx: discord.AutocompleteContext):
    room, path = discape.get_player_location(ctx.interaction.user.name)
    if room:
        return discape.get_zones(ctx.interaction.user.name) + (
            ["↩️ Volver"] if room and path else []
        )
    else:
        return []


@escape.command(name="investigar", description="Investiga en la sala de huida.")
@option(
    "objetivo",
    description="¿Qué quieres investigar?",
    autocomplete=discord.utils.basic_autocomplete(get_investigation_options),
)
async def investigate(ctx: discord.ApplicationContext, objetivo: str):
    """Investiga en la sala de huida."""
    await ctx.respond(discape.take_path(ctx.interaction.user.name, objetivo))


@escape.command(name="objetos", description="Muestra los objetos de tu inventario.")
async def inventory(ctx: discord.ApplicationContext):
    """Muestra los objetos de tu inventario."""
    inventory = discape.get_inventory_dict(
        discape.get_player_location(ctx.interaction.user.name)[0]
    )
    embeds = []
    for item in inventory:
        embed = discord.Embed(title=item, description=inventory[item])
        embeds.append(embed)
    if embeds:
        view = discape.PaginationView(embeds)
        await ctx.respond(embed=embeds[0], view=view, ephemeral=True)
    else:
        await ctx.respond("No tienes ningún objeto.", ephemeral=True)


async def get_equipable_items(ctx: discord.AutocompleteContext):
    return discape.get_inventory_names(
        discape.get_player_location(ctx.interaction.user.name)[0]
    )


@escape.command(name="equipar", description="Equipar un objeto.")
@option(
    "objeto",
    description="¿Qué objeto quieres equipar?",
    autocomplete=discord.utils.basic_autocomplete(get_equipable_items),
)
async def equip(ctx: discord.ApplicationContext, objeto: str):
    """Equipar un objeto."""
    await ctx.respond(discape.equip(ctx.interaction.user.name, objeto))


@escape.command(name="combinar", description="Combina dos objetos.")
@option(
    "objeto1",
    description="¿Qué objeto quieres combinar?",
    autocomplete=discord.utils.basic_autocomplete(get_equipable_items),
)
@option(
    "objeto2",
    description="¿Con qué objeto quieres combinarlo?",
    autocomplete=discord.utils.basic_autocomplete(get_equipable_items),
)
async def combine(ctx: discord.ApplicationContext, objeto1: str, objeto2: str):
    """Combina dos objetos."""
    await ctx.respond(
        discape.combine(
            objeto1, objeto2, discape.get_player_location(ctx.interaction.user.name)[0]
        )
    )


@escape.command(name="unirse", description="Unirse a una partida de sala de huida.")
async def join(ctx: discord.ApplicationContext):
    """Unirse a una partida de sala de huida."""
    (room, _) = discape.get_player_location(ctx.interaction.user.name)
    if room:
        await ctx.respond(
            "Aún no has escapado de la sala de huida en la que estás.", ephemeral=True
        )
    else:
        await ctx.respond(
            discape.join_room(ctx.interaction.user.name, ctx.interaction.channel.name)
        )


@mission.command(name="solicitar", description="Solicita una misión.")
async def request(ctx: discord.ApplicationContext):
    """Solicita una misión."""
    response = quests.create_request(conn_que, ctx.interaction.user.name)
    if response == -1:
        await ctx.respond("Ya tienes una solicitud de misión en curso.", ephemeral=True)
    else:
        # Send a message to the quest-requests channel
        channel = QUEST_REQUESTS_CHANNEL_ID
        embed = discord.Embed(
            title="Nueva solicitud de misión",
            description=f"**Solicitante:** {ctx.interaction.user.name}",
        )
        await bot.get_channel(channel).send(embed=embed)

        # Send a message to the player
        await ctx.respond("Solicitud de misión enviada.", ephemeral=True)


@mission.command(name="crear", description="Crea una misión.")
@option(
    "jugador",
    description="Jugador al que asignar la misión.",
    choices=quests.get_users_with_pending_requests(conn_que),
    required=True,
)
@option("descripción", description="Descripción de la misión.", required=True)
@option("recompensa", description="Recompensa de la misión.", required=True)
async def create(
    ctx: discord.ApplicationContext, jugador: str, descripción: str, recompensa: str
):
    """Crea una misión."""
    try:
        request_id = quests.get_user_request_id(conn_que, jugador)
        quests.update_request(conn_que, jugador, descripción, recompensa)
        # Send a message to the user's quest channel, which is stored in a dictionary
        embed = discord.Embed(
            author=discord.EmbedAuthor(name=f"Misión n.º {request_id}"),
            title=descripción,
            fields=[
                discord.EmbedField(name="Recompensa", value=recompensa),
            ],
        )
        await bot.get_channel(QUEST_CHANNEL_ID_DICT[jugador]).send(embed=embed)
        await ctx.respond("Misión creada.")
    except Exception as e:
        await ctx.respond(f"Error: {e}", ephemeral=True)


def get_quest_options(ctx: discord.AutocompleteContext):
    records = quests.get_user_active_quests(conn_que, ctx.interaction.user.name)
    return [f"{record[0]}: {record[2]}" for record in records]


@mission.command(name="completar", description="Completa una misión.")
@option(
    "misión",
    description="Misión que has completado.",
    autocomplete=discord.utils.basic_autocomplete(get_quest_options),
)
async def complete(ctx: discord.ApplicationContext, misión: str):
    # Get the last message in the channel where the command was invoked
    last_message = await ctx.interaction.channel.history(limit=1).flatten()
    if last_message:
        last_message_link = last_message[0].jump_url
    else:
        channel_name = ctx.interaction.channel.name
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        last_message_link = f"In channel '{channel_name}' at {current_time}"

    # Send a message to the completed_quest channel with the link to the last message
    embed = discord.Embed(
        title="Misión completada",
        description=f"{ctx.interaction.user.name} ha completado la misión «{misión}».\n\n[Enlace al último mensaje]({last_message_link})",
    )
    message = await bot.get_channel(COMPLETED_QUESTS_CHANNEL_ID).send(embed=embed)
    await message.add_reaction("✅")  # Checkmark reaction
    await message.add_reaction("❌")  # Cross reaction

    await ctx.respond("Misión completada.", ephemeral=True)


bot.run(TOKEN)
