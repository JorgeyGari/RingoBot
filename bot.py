import discord
from discord import option
import os
from dotenv import load_dotenv

import replies
import dice

import discape

intents = discord.Intents.all()

load_dotenv()
bot = discord.Bot(debug_guilds=[429400823395647489], intents=intents)


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


@escape.command(name="iniciar", description="Inicia una partida de sala de huida.")
@option("archivo", description="Archivo de sala de huida.", required=True)
async def iniciar(ctx: discord.ApplicationContext, archivo: discord.Attachment):
    """Inicia una partida de sala de huida."""
    # Save the file
    await archivo.save("file.xlsx")
    # Check if the file is valid
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
    return discape.get_zones(ctx.interaction.user.name) + (
        ["↩️ Volver"] if room and path else []
    )


@escape.command(name="investigar", description="Investiga en la sala de huida.")
@option(
    "objetivo",
    description="¿Qué quieres investigar?",
    autocomplete=discord.utils.basic_autocomplete(get_investigation_options),
)
async def investigate(ctx: discord.ApplicationContext, objetivo: str):
    """Investiga en la sala de huida."""
    await ctx.respond(discape.take_path(ctx.interaction.user.name, objetivo))


bot.run(os.getenv("TOKEN"))
