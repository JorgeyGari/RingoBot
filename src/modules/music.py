"""
Music module for YouTube music playback functionality.
"""

import asyncio
import logging
import os
import shutil

import discord
import yt_dlp

from utils.config import config

logger = logging.getLogger(__name__)


class MusicModule:
    """Handles YouTube music playback functionality."""

    def __init__(self):
        """Initialize the music module."""
        # Ensure downloads directory exists
        try:
            os.makedirs(config.DOWNLOADS_DIR, exist_ok=True)
        except OSError as e:
            logger.error(f"No se pudo crear el directorio de descargas: {e}")

        # Check for FFmpeg availability
        self.ffmpeg_path = shutil.which("ffmpeg")

    def download_audio(self, link: str) -> str:
        """
        Download audio from YouTube and return the file path.

        Args:
            link: YouTube video URL

        Returns:
            Path to downloaded audio file

        Raises:
            yt_dlp.DownloadError: If download fails
        """
        # yt-dlp types its params as a private TypedDict; a plain dict works.
        with yt_dlp.YoutubeDL(config.YTDL_OPTS) as ydl:  # pyright: ignore[reportArgumentType]
            info = ydl.extract_info(link, download=True)
            filename = ydl.prepare_filename(info)
            # Replace extension with .mp3
            base_name, _ = os.path.splitext(filename)
            return base_name + ".mp3"

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

            if not self.ffmpeg_path:
                await ctx.followup.send("No se encontró el ejecutable de FFmpeg.", ephemeral=True)
                return

            vc = await voice_channel.connect()

            # Off the event loop: yt-dlp plus ffmpeg block for seconds
            audio_file = await asyncio.to_thread(self.download_audio, link)

            title = os.path.basename(audio_file).replace("_", " ").replace(".mp3", "")

            def _finished(error):
                if error:
                    logger.error(f"Error de reproducción: {error}")
                try:
                    os.remove(audio_file)
                except OSError:
                    logger.warning(f"Could not remove audio file: {audio_file}")
                # Called from the player thread, not the event loop
                asyncio.run_coroutine_threadsafe(vc.disconnect(), bot.loop)

            vc.play(
                discord.FFmpegPCMAudio(executable=self.ffmpeg_path, source=audio_file),
                after=_finished,
            )

            await ctx.followup.send(f"Reproduciendo: **{title}**")
            logger.info(f"Started playing music: {title}")

        except Exception as e:
            logger.error(f"Error playing music: {e}")

            try:
                await ctx.followup.send(f"Error al reproducir música: {e}", ephemeral=True)
            except discord.HTTPException:
                pass

            # Ensure we disconnect on error
            if ctx.guild and ctx.guild.voice_client:
                await ctx.guild.voice_client.disconnect()
