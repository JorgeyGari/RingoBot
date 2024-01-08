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


class PaginationView(discord.ui.View):
    def __init__(self, embeds):
        super().__init__()
        self.embeds = embeds
        self.current = 0

    async def update_page(self, interaction: discord.Interaction):
        self.embeds[self.current].set_footer(
            text=f"Página {self.current + 1} de {len(self.embeds)}"
        )
        await interaction.response.edit_message(embed=self.embeds[self.current])

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.blurple)
    async def previous_page(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.current = (self.current - 1) % len(self.embeds)
        await self.update_page(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.blurple)
    async def next_page(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.current = (self.current + 1) % len(self.embeds)
        await self.update_page(interaction)


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


@escape.command(name="objetos", description="Muestra los objetos de tu inventario.")
async def inventory(ctx: discord.ApplicationContext):
    """Muestra los objetos de tu inventario."""
    inventory = discape.get_inventory_dict()
    embeds = []
    for item in inventory:
        embed = discord.Embed(title=item, description=inventory[item])
        embeds.append(embed)
    if embeds:
        view = PaginationView(embeds)
        await ctx.respond(embed=embeds[0], view=view, ephemeral=True)
    else:
        await ctx.respond("No tienes ningún objeto.", ephemeral=True)


async def get_equipable_items(ctx: discord.AutocompleteContext):
    return discape.get_inventory_names()


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
    await ctx.respond(discape.combine(objeto1, objeto2))

@escape.command(name="unirse", description="Unirse a una partida de sala de huida.")
async def join(ctx: discord.ApplicationContext):
    """Unirse a una partida de sala de huida."""
    await ctx.respond(discape.join_room(ctx.interaction.user.name, ctx.interaction.channel.name))


bot.run(os.getenv("TOKEN"))
