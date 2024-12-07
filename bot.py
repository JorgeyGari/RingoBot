import discord
from discord import option
import os
from dotenv import load_dotenv
import yt_dlp

import replies
import dice
import discape
import quests
from music import play_youtube_music

from config import *
import datetime
import asyncio

intents = discord.Intents.all()

load_dotenv()
bot = discord.Bot(debug_guilds=[429400823395647489, 948015933434253372], intents=intents)
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

@bot.slash_command(name="ytmusic", description="Reproduce música de YouTube en tu canal de voz.")
@option("link", description="Enlace del video de YouTube.", required=True)
async def ytmusic(ctx: discord.ApplicationContext, link: str):
    """Reproduce música de YouTube en tu canal de voz."""
    await play_youtube_music(ctx, bot, link)

bot.run(TOKEN)
