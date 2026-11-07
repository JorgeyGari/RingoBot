"""Discord scheduled events: mention everyone who marked interest in one."""

import logging

import discord

from utils.parse import to_int

logger = logging.getLogger(__name__)


class EventsModule:
    """Reads guild scheduled events and pings their interested subscribers."""

    def get_event_options(self, guild) -> list[str]:
        """Autocomplete choices: event names."""
        if guild is None:
            return []
        return [event.name for event in guild.scheduled_events][:25]

    @staticmethod
    def _find_event(events, query: str):
        """Resolve an event by name, case-insensitive, exact first then substring."""
        query = query.strip().casefold()
        for event in events:
            if event.name.casefold() == query:
                return event
        for event in events:
            if query in event.name.casefold():
                return event
        return None

    @staticmethod
    def _chunk_mentions(mentions: list[str], limit: int = 1900) -> list[str]:
        """Pack mentions into messages under Discord's 2000-char cap."""
        chunks, current = [], ""
        for mention in mentions:
            candidate = f"{current} {mention}" if current else mention
            if len(candidate) > limit:
                chunks.append(current)
                current = mention
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks

    async def handle_mention_command(self, ctx, evento: str, mensaje: str | None = None):
        """Mention every user subscribed (interested) to an event."""
        guild = ctx.guild
        if guild is None:
            await ctx.respond("Esto solo funciona dentro de un servidor.", ephemeral=True)
            return

        event = self._find_event(guild.scheduled_events, evento)
        if event is None:
            await ctx.respond(
                f"No encuentro ningún evento que se llame «{evento}».", ephemeral=True
            )
            return

        await ctx.defer(ephemeral=True)  # placeholder is private; pings go out as fresh messages
        try:
            members = await event.subscribers(limit=None, as_member=True).flatten()
        except discord.HTTPException:
            logger.exception("No pude leer los interesados del evento %s", event.id)
            await ctx.followup.send("Discord no me deja ver quién está interesado en ese evento.")
            return

        mentions = [member.mention for member in members if not member.bot]
        if not mentions:
            await ctx.followup.send(f"Todavía nadie ha marcado interés en **{event.name}**.")
            return

        header = f"🔔 **{event.name}** — <t:{to_int(event.start_time.timestamp())}:f> (pedido por {ctx.author.mention})"
        if mensaje:
            header += f"\n{mensaje}"
        header += "\n"
        chunks = self._chunk_mentions(mentions)
        if len(header) + len(chunks[0]) <= 1900:
            chunks[0] = header + chunks[0]
        else:
            chunks.insert(0, header)
        allowed = discord.AllowedMentions(users=True, everyone=False, roles=False)
        for chunk in chunks:
            await ctx.channel.send(chunk, allowed_mentions=allowed)
        await ctx.followup.send(f"He avisado a las personas interesadas en **{event.name}**.")
        logger.info(
            "Mencionados %d interesados en el evento %s (%s)",
            len(mentions),
            event.name,
            event.id,
        )


if __name__ == "__main__":  # self-check: cd src && python -m modules.events
    from types import SimpleNamespace

    chunk = EventsModule._chunk_mentions
    assert chunk([]) == []
    assert chunk(["<@1>", "<@2>"], limit=100) == ["<@1> <@2>"]
    assert chunk(["<@1>", "<@2>"], limit=6) == ["<@1>", "<@2>"]
    assert chunk(["<@1>"] * 3, limit=12) == ["<@1> <@1>", "<@1>"]

    events = [SimpleNamespace(name="Noche de rol"), SimpleNamespace(name="Cena")]
    find = EventsModule._find_event
    assert find(events, "noche de rol") is events[0]
    assert find(events, "CENA") is events[1]
    assert find(events, "rol") is events[0]
    assert find(events, "nada") is None
    print("events self-check ok")
