import discord
from discord import app_commands

import responses
import dice
import characters
import tienda


def character_setup() -> dict:
    """Crea los entrenadores y les añade sus habilidades, devuelve un diccionario que los asigna a sus jugadores."""

    lana = characters.Trainer('Lana')
    lana.add_ability('engañar', 4)
    lana.add_ability('investigar', 3)
    lana.add_ability('atletismo', 3)
    lana.add_ability('saber', 2)
    lana.add_ability('sigilo', 2)
    lana.add_ability('carisma', 2)
    lana.add_ability('voluntad', 1)
    lana.add_ability('percepción', 1)
    lana.add_ability('conocimientos', 1)
    lana.add_ability('físico', 1)

    kai = characters.Trainer('Kai')
    kai.add_ability('conocimientos', 4)
    kai.add_ability('físico', 3)
    kai.add_ability('percepción', 3)
    kai.add_ability('pelea', 2)
    kai.add_ability('atletismo', 2)
    kai.add_ability('voluntad', 2)
    kai.add_ability('empatía', 1)
    kai.add_ability('investigar', 1)
    kai.add_ability('pelea', 1)
    kai.add_ability('lanzar', 1)

    vivi = characters.Trainer('Vivi')
    vivi.add_ability('carisma', 4)
    vivi.add_ability('engañar', 3)
    vivi.add_ability('atletismo', 3)
    vivi.add_ability('físico', 2)
    vivi.add_ability('pelea', 2)
    vivi.add_ability('sigilo', 2)
    vivi.add_ability('empatía', 1)
    vivi.add_ability('recursos', 1)
    vivi.add_ability('percepción', 1)
    vivi.add_ability('investigar', 1)

    player = {
        'Zen#1641': lana,
        'Niter#1675': kai,
        'Luc#5307': vivi
    }

    return player


async def send_message(message, user_message, is_private):
    try:
        response = responses.handle_response(user_message)
        if response is not None:
            await message.author.send(response) if is_private else await message.channel.send(response)
    except Exception as e:
        print(e)


def run_discord_bot():
    TOKEN = 'MTA1OTE1NDA4MjgxNzkxNzA0OQ.GtNZPu.u91NUr1KasPyrs-ZMtAYzDTy_CHrQYpzaGwzME'
    client = discord.Client(intents=discord.Intents.all())
    tree = app_commands.CommandTree(client)

    character_setup()

    @client.event
    async def on_ready():
        print(f'{client.user} se ha conectado a Discord.')
        await client.change_presence(activity=discord.Game(name='!ayuda'))
        await tree.sync(guild=discord.Object(id=429400823395647489))

    @client.event
    async def on_message(message):
        if message.author == client.user:
            return

        username = str(message.author)
        user_message = str(message.content)
        channel = str(message.channel)

        print(f'{username} ha enviado un mensaje en #{channel}: {user_message}')

        if user_message.startswith('!ayuda'):
            user_message = '$' + user_message

        if user_message[0] == '$':
            user_message = user_message[1:]
            await send_message(message, user_message, is_private=True)
        else:
            await send_message(message, user_message, is_private=False)

    @tree.command(name="roll", description="Tirar dados", guild=discord.Object(id=429400823395647489))
    async def roll_dice(interaction: discord.Interaction, dado: str, modificador: int = 0):
        if dice.invalid(dado):
            err_msg = dice.invalid(dado)
            await interaction.response.send_message(err_msg)
            return

        roll = dice.roll_dice(dado)

        message = f"¡{interaction.user} ha tirado {dice.human_read(dado)}!\n" \
                  f"```{roll}\nTOTAL: {dice.total_roll(roll)}"
        if modificador != 0:
            message += f" + {modificador} = {dice.total_roll(roll) + modificador}```"
        else:
            message += '```'

        await interaction.response.send_message(message)

    @tree.command(name="habilidad", description="Usar una habilidad de tu personaje",
                  guild=discord.Object(id=429400823395647489))
    async def use_ability(interaction: discord.Interaction, nombre: str):
        player = character_setup()
        trainer = player[str(interaction.user)]
        nombre = nombre.lower()
        if nombre not in trainer.moves:
            await interaction.response.send_message(f"¡{trainer.name} no tiene habilidades de {nombre}!")
            return

        roll = dice.roll_dice('4df')

        message = f"¡{trainer.name} ha usado sus habilidades de {nombre}!\n" \
                  f"```{roll}\nTOTAL: {dice.total_roll(roll)}"
        if trainer.moves[nombre] != 0:
            message += f" + {trainer.moves[nombre]} = " \
                       f"{dice.total_roll(roll) + trainer.moves[nombre]}```"
        else:
            message += '```'

        await interaction.response.send_message(message)

    @tree.command(name="tienda", description="Interactuar con la tienda de objetos", guild=discord.Object(id=429400823395647489))
    async def shop(interaction: discord.Interaction, compra: str = None):
        if compra is None:
            await interaction.response.send_message(tienda.inventory())
            return

        await interaction.response.send_message(tienda.buy(compra))

    client.run(TOKEN)
