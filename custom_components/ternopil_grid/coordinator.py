from __future__ import annotations

from datetime import datetime, timedelta, timezone

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import fetch_schedule
from .ping import tcp_ping
from .const import (
    DOMAIN,
    DEFAULT_PING_INTERVAL,
    DEFAULT_PING_IP,
    DEFAULT_PING_PORT,
    DEFAULT_PING_TIMEOUT,
)


def _ts(dt: datetime) -> float:
    return dt.timestamp()


class TernopilScheduleCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, group: str):
        self.group = group
        super().__init__(
            hass=hass,
            logger=hass.logger,
            name=f"{DOMAIN}_schedule",
            update_interval=timedelta(minutes=15),
        )

    async def _async_update_data(self):
        try:
            session = async_get_clientsession(self.hass)
            raw = await fetch_schedule(session, self.group)

            # The endpoint returns schedule graph data; we normalize into 30-min segments for today+tomorrow
            # We'll accept either:
            # - list of points (time -> value), OR
            # - dict style with times
            # Since API formats can change, we implement tolerant parsing:
            segments = []

            # Try to find "times" dict:
            times = None
            if isinstance(raw, dict):
                # common patterns
                if "times" in raw and isinstance(raw["times"], dict):
                    times = raw["times"]
                elif "data" in raw and isinstance(raw["data"], dict) and "times" in raw["data"]:
                    times = raw["data"]["times"]
                elif "hydra:member" in raw:
                    # fall back if it ever matches older style
                    pass

            # Build segments based on today UTC day start (local is fine; schedule is relative anyway)
            base = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

            def color_from_val(v: str) -> str:
                return "red" if v == "1" else "yellow" if v == "10" else "green"

            if isinstance(times, dict):
                # expect keys "HH:MM" with "0"/"1"/"10"
                for day_offset in (0, 1):  # today + tomorrow
                    day_base = base + timedelta(days=day_offset)
                    for i in range(48):
                        h = i // 2
                        m = 30 if i % 2 else 0
                        key = f"{h:02d}:{m:02d}"
                        v = str(times.get(key, "0"))
                        s = _ts(day_base.replace(hour=h, minute=m))
                        e = s + 1800
                        segments.append({"start": s, "end": e, "color": color_from_val(v)})
                return segments

            # If we can't parse, still return empty list (entities become unavailable via last_update_success)
            return segments

        except Exception as err:
            raise UpdateFailed(str(err)) from err


class TernopilPingCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, ip: str, port: int, timeout_s: float, interval_s: float):
        self.ip = ip or DEFAULT_PING_IP
        self.port = int(port) if port else DEFAULT_PING_PORT
        self.timeout_s = float(timeout_s) if timeout_s else DEFAULT_PING_TIMEOUT
        self.interval_s = float(interval_s) if interval_s else DEFAULT_PING_INTERVAL

        super().__init__(
            hass=hass,
            logger=hass.logger,
            name=f"{DOMAIN}_ping",
            update_interval=timedelta(seconds=self.interval_s),
        )

    async def _async_update_data(self):
        ok = await tcp_ping(self.ip, self.port, self.timeout_s)
        return {"ok": ok, "ip": self.ip, "port": self.port}
