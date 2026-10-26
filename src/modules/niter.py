"""Niter's shift lookup, read from a hand-edited Discord message."""

import calendar
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import discord

from utils.config import config
from modules.wisdom import _normalize

logger = logging.getLogger(__name__)

SHIFTS = {
    "m": "mañana",
    "manana": "mañana",
    "t": "tarde",
    "tarde": "tarde",
    "n": "noche",
    "noche": "noche",
}
OFF = {"l", "libre", "descanso", "d", "-", "x"}
WEEKDAYS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
WEEKDAYS_ACCENTED = [
    "lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo",
]
MONTHS = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

_LINE_RE = re.compile(
    r"^(?:del?\s+)?(?P<d1>\d{1,2})(?:[/.](?P<m1>\d{1,2}))?"
    r"(?:\s*(?:al|a|-|–|hasta)\s*(?P<d2>\d{1,2})(?:[/.](?P<m2>\d{1,2}))?)?"
    r"\s*[:=\-–>]*\s*(?P<code>[a-z]+|-)\s*\.?$"
)
_HEADER_RE = re.compile(r"^(?P<mes>[a-z]+)(?:\s+(?:de\s+)?(?P<year>\d{4}))?\s*:?$")
_DECOR_RE = re.compile(r"[*_~`>]")
_BULLET_RE = re.compile(r"^[\s\-•]+")


@dataclass
class Schedule:
    days: dict[date, str | None]
    start: date
    end: date
    updated: date


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _closest(day: int, anchor: date, month: int | None = None) -> date | None:
    """Candidate date with given day (and month, if any) closest to anchor."""
    cands = []
    if month is None:
        for delta in (-1, 0, 1):
            y, m = _add_months(anchor.year, anchor.month, delta)
            c = _safe_date(y, m, day)
            if c:
                cands.append(c)
    else:
        for y in (anchor.year - 1, anchor.year, anchor.year + 1):
            c = _safe_date(y, month, day)
            if c:
                cands.append(c)
    if not cands:
        return None
    # ties -> later
    return min(cands, key=lambda c: (abs((c - anchor).days), -c.toordinal()))


def parse_schedule(text: str, anchor: date) -> Schedule | None:
    days: dict[date, str | None] = {}
    prev_end: date | None = None
    header_month: int | None = None  # set by a "Octubre" / "Octubre 2026" line
    header_year: int | None = None

    for raw in text.splitlines():
        line = _DECOR_RE.sub("", raw)
        line = _BULLET_RE.sub("", line)
        line = _normalize(line.strip()).strip()
        h = _HEADER_RE.match(line)
        if h and h["mes"] in MONTHS:
            header_month = MONTHS[h["mes"]]
            header_year = int(h["year"]) if h["year"] else None
            continue
        m = _LINE_RE.match(line)
        if not m:
            continue
        code = m["code"]
        if code in SHIFTS:
            shift: str | None = SHIFTS[code]
        elif code in OFF:
            shift = None
        else:
            logger.warning("Unrecognised shift line: %r", raw)
            continue

        d1, d2 = int(m["d1"]), int(m["d2"]) if m["d2"] else None
        m1 = int(m["m1"]) if m["m1"] else None
        m2 = int(m["m2"]) if m["m2"] else None

        if m1 is not None:
            start = _closest(d1, anchor, m1)
        elif header_month is not None:
            if header_year is not None:
                start = _safe_date(header_year, header_month, d1)
            else:
                start = _closest(d1, anchor, header_month)
        elif prev_end is None:
            start = _closest(d1, anchor)
        else:
            y, mo = prev_end.year, prev_end.month
            if d1 < prev_end.day:
                y, mo = _add_months(y, mo, 1)
            start = _safe_date(y, mo, d1)
        if start is None:
            logger.warning("Invalid date in schedule line: %r", raw)
            continue

        end = start
        if d2 is not None:
            if m2 is not None:
                end = _safe_date(start.year, m2, d2)
                if end is not None and end < start:
                    end = _safe_date(start.year + 1, m2, d2)
            else:
                end = _safe_date(start.year, start.month, d2)
                if d2 < d1:
                    y, mo = _add_months(start.year, start.month, 1)
                    end = _safe_date(y, mo, d2)
            if end is None or end < start:
                logger.warning("Invalid date range in schedule line: %r", raw)
                continue

        cur = start
        while cur <= end:
            days[cur] = shift
            cur += timedelta(days=1)
        prev_end = end

    if not days:
        return None
    return Schedule(days=days, start=min(days), end=max(days), updated=anchor)


def parse_target(arg: str | None, today: date) -> date | None:
    s = _normalize(arg or "").strip()
    s = re.sub(r"^(?:el|este|para)\s+", "", s).strip()
    if s in ("", "hoy"):
        return today
    if s == "manana":
        return today + timedelta(days=1)
    if s == "pasado manana":
        return today + timedelta(days=2)
    if s == "ayer":
        return today - timedelta(days=1)

    m = re.fullmatch(r"(?:proximo\s+)?(\w+?)(\s+que\s+viene)?", s)
    if m and m[1] in WEEKDAYS:
        strict = bool(m[2]) or s.startswith("proximo ")
        delta = (WEEKDAYS.index(m[1]) - today.weekday()) % 7
        if strict and delta == 0:
            delta = 7
        return today + timedelta(days=delta)

    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return _safe_date(int(m[1]), int(m[2]), int(m[3]))

    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4}|\d{2})", s)
    if m:
        y = int(m[3])
        if y < 100:
            y += 2000
        return _safe_date(y, int(m[2]), int(m[1]))

    month = None
    m = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})", s)
    if m:
        d, month = int(m[1]), int(m[2])
    else:
        m = re.fullmatch(r"(\d{1,2})\s+de\s+([a-z]+)", s)
        if m and m[2] in MONTHS:
            d, month = int(m[1]), MONTHS[m[2]]
    if month is not None:
        r = _safe_date(today.year, month, d)
        if r is None:
            return None
        if (today - r).days > 180:
            r = _safe_date(today.year + 1, month, d)
        return r

    m = re.fullmatch(r"(?:dia\s+)?(\d{1,2})", s)
    if m:
        d = int(m[1])
        if d >= today.day:
            return _safe_date(today.year, today.month, d)
        y, mo = _add_months(today.year, today.month, 1)
        return _safe_date(y, mo, d)
    return None


def describe(target: date, today: date) -> str:
    named = {0: "Hoy", 1: "Mañana", 2: "Pasado mañana", -1: "Ayer"}
    off = (target - today).days
    if off in named:
        return named[off]
    return f"El {WEEKDAYS_ACCENTED[target.weekday()]} {target:%d/%m}"


class NiterModule:
    async def handle_nitercurro_command(
        self, ctx: discord.ApplicationContext, cuando: str | None
    ):
        tz = ZoneInfo(config.TIMEZONE)
        today = datetime.now(tz).date()
        target = parse_target(cuando, today)
        if target is None:
            await ctx.respond(
                f"No entiendo la fecha «{cuando}». Prueba con «mañana», «el jueves» o «27/10».",
                ephemeral=True,
            )
            return

        try:
            channel = ctx.bot.get_channel(
                config.NITER_SCHEDULE_CHANNEL_ID
            ) or await ctx.bot.fetch_channel(config.NITER_SCHEDULE_CHANNEL_ID)
            msg = await channel.fetch_message(config.NITER_SCHEDULE_MESSAGE_ID)
        except discord.HTTPException as e:
            logger.error("Could not fetch Niter schedule message: %s", e)
            await ctx.respond("❌ No he podido leer el horario de Niter.", ephemeral=True)
            return

        anchor = (msg.edited_at or msg.created_at).astimezone(tz).date()
        schedule = parse_schedule(msg.content, anchor)
        if schedule is None:
            logger.warning("Could not parse Niter schedule: %r", msg.content)
            await ctx.respond(
                "❌ No he podido entender el horario de Niter.", ephemeral=True
            )
            return

        subject = describe(target, today)
        footer = f"-# Horario actualizado el {schedule.updated:%d/%m}."
        if target < schedule.start or target > schedule.end:
            await ctx.respond(
                f"No tengo el horario de Niter para {subject[0].lower() + subject[1:]}. "
                f"El horario va del {schedule.start:%d/%m} al {schedule.end:%d/%m}.\n{footer}"
            )
            return
        shift = schedule.days.get(target)
        if shift:
            await ctx.respond(f"{subject} Niter curra por la **{shift}**.\n{footer}")
        else:
            await ctx.respond(f"{subject} Niter no curra.\n{footer}")
