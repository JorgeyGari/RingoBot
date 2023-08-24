import discord
from discord import option
import os
from dotenv import load_dotenv

import replies
import dice

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
        if message.content.startswith('$'):
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
@option("dados", description="Cantidad y tipo de dado a tirar. Por ejemplo, \"2d6\", \"1d20\" o \"4df\".")
@option("modificador", description="Modificador a aplicar a la tirada. Por ejemplo, \"+2\" o \"-1\".",
        default=0, required=False)
async def dado(
    ctx: discord.ApplicationContext,
    dados: str,
    modificador: int
):
    """Tirar dados."""
    if dice.invalid(dados):
        await ctx.respond(dice.invalid(dados), ephemeral=True)
        return
    roll = dice.roll_dice(dados)
    total_roll = dice.total_roll(roll) + modificador
    await ctx.respond(f"¡Has tirado {dice.human_read(dados)}!\n"
                      f"`{roll}`\n"
                      f"**Total:** {total_roll}")

bot.run(os.getenv('TOKEN'))
