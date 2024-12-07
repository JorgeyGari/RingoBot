import os
import yt_dlp
import discord
import asyncio


def download_audio(link):
    """
    Download audio from YouTube and return the file path.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'noplaylist': True,  # Only download the first song if it's a playlist
        'postprocessor_args': ['-t', '1800']  # Limit to the first 30 minutes
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            return ydl.prepare_filename(info).replace(".webm", ".mp3")  # Adjust if needed
    except Exception as e:
        raise Exception(f"Error downloading audio: {e}")


async def play_youtube_music(ctx, bot, link):
    """
    Handle connecting to a voice channel, downloading, and playing YouTube music.
    """
    if not ctx.author.voice:
        await ctx.respond("Debes estar en un canal de voz para usar este comando.", ephemeral=True)
        return

    voice_channel = ctx.author.voice.channel

    try:
        await ctx.respond("Descargando y reproduciendo música...", ephemeral=True)

        # Join the voice channel
        vc = await voice_channel.connect()

        # Download the audio
        audio_file = download_audio(link)

        # Play the audio
        vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=audio_file))

        # Send a message with the title of the playing audio
        await ctx.send(f"Reproduciendo: **{os.path.basename(audio_file).replace('_', ' ').replace('.mp3', '')}**")

        while vc.is_playing():
            await asyncio.sleep(1)

        # Disconnect after playing
        await vc.disconnect()

        # Clean up the audio file
        os.remove(audio_file)

        await ctx.respond("¡Reproducción terminada!", ephemeral=True)

    except Exception as e:
        await ctx.respond(f"Error al reproducir música: {e}", ephemeral=True)
        if ctx.guild.voice_client:
            await ctx.guild.voice_client.disconnect()
