from __future__ import annotations

import aiohttp
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from .const import API_URL, SCHEDULE_DAYS


def _iso_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


async def fetch_schedule(session: aiohttp.ClientSession, group: str) -> dict:
    now = datetime.now(timezone.utc)
    after = now.replace(hour=0, minute=0, second=0, microsecond=0)
    before = after + timedelta(days=SCHEDULE_DAYS)

    params = [
        ("after", _iso_utc(after)),
        ("before", _iso_utc(before)),
        ("group[]", group),
    ]
    url = f"{API_URL}?{urlencode(params)}"

    async with session.get(url, timeout=30) as resp:
        resp.raise_for_status()
        return await resp.json()
