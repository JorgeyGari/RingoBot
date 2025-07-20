"""
Music module for YouTube music playback functionality.
"""

import os
import yt_dlp
import discord
from discord.ext import commands
import asyncio
import logging

from utils.config import config

logger = logging.getLogger(__name__)


class MusicModule:
    """Handles YouTube music playback functionality."""

    def __init__(self):
        """Initialize the music module."""
        # Ensure downloads directory exists
        os.makedirs(config.DOWNLOADS_DIR, exist_ok=True)

    def download_audio(self, link: str) -> str:
        """
        Download audio from YouTube and return the file path.

        Args:
            link: YouTube video URL

        Returns:
            Path to downloaded audio file

        Raises:
            Exception: If download fails
        """
        try:
            with yt_dlp.YoutubeDL(config.YTDL_OPTS) as ydl:
                info = ydl.extract_info(link, download=True)
                filename = ydl.prepare_filename(info)
                # Replace extension with .mp3
                base_name, _ = os.path.splitext(filename)
                audio_file = base_name + ".mp3"
                return audio_file
        except Exception as e:
            logger.error(f"Error downloading audio: {e}")
            raise Exception(f"Error downloading audio: {e}")

    async def play_youtube_music(self, ctx, bot, link: str):
        """
        Handle YouTube music playback command.

        Args:
            ctx: Discord application context
            bot: Discord bot instance
            link: YouTube video URL
        """
        # Check if user is in a voice channel
        if not ctx.author.voice:
            await ctx.respond(
                "Debes estar en un canal de voz para usar este comando.", ephemeral=True
            )
            return

        voice_channel = ctx.author.voice.channel

        try:
            await ctx.respond("Descargando y reproduciendo música...", ephemeral=True)

            # Join the voice channel
            vc = await voice_channel.connect()

            # Download the audio
            audio_file = self.download_audio(link)

            # Play the audio
            if not self.ffmpeg_available:
                await ctx.send(
                    "No se encontró el ejecutable de FFmpeg.", ephemeral=True
                )
                await vc.disconnect()
                return
            vc.play(discord.FFmpegPCMAudio(executable=ffmpeg_path, source=audio_file))

            # Get the title from filename
            title = os.path.basename(audio_file).replace("_", " ").replace(".mp3", "")

            # Send playing message
            await ctx.send(f"Reproduciendo: **{title}**")

            # Wait for playback to finish
            while vc.is_playing():
                await asyncio.sleep(1)

            # Disconnect and cleanup
            await vc.disconnect()

            # Clean up the audio file
            try:
                os.remove(audio_file)
            except OSError:
                logger.warning(f"Could not remove audio file: {audio_file}")

            await ctx.followup.send("¡Reproducción terminada!", ephemeral=True)
            logger.info(f"Successfully played music: {title}")

        except Exception as e:
            logger.error(f"Error playing music: {e}")
            await ctx.respond(f"Error al reproducir música: {e}", ephemeral=True)

            # Ensure we disconnect on error
            if ctx.guild.voice_client:
                await ctx.guild.voice_client.disconnect()
