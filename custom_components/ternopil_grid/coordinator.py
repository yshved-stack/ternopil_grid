from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import fetch_schedule
from .const import (
    DEFAULT_PING_INTERVAL,
    DEFAULT_PING_IP,
    DEFAULT_PING_PORT,
    DEFAULT_PING_TIMEOUT,
    DOMAIN,
)
from .ping import tcp_ping

_LOGGER = logging.getLogger(__name__)


def _ts(dt: datetime) -> float:
    return dt.timestamp()


class TernopilScheduleCoordinator(DataUpdateCoordinator[list[dict]]):
    def __init__(self, hass, group: str):
        self.group = group
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_schedule",
            update_interval=timedelta(minutes=15),
        )

    async def _async_update_data(self) -> list[dict]:
        try:
            session = async_get_clientsession(self.hass)
            raw = await fetch_schedule(session, self.group)

            segments: list[dict] = []
            times = None

            if isinstance(raw, dict):
                if "times" in raw and isinstance(raw["times"], dict):
                    times = raw["times"]
                elif "data" in raw and isinstance(raw["data"], dict) and "times" in raw["data"]:
                    times = raw["data"]["times"]

            base = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

            def color_from_val(v: str) -> str:
                return "red" if v == "1" else "yellow" if v == "10" else "green"

            if isinstance(times, dict):
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

        except Exception as err:
            raise UpdateFailed(str(err)) from err


class TernopilPingCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass, ip: str, port: int, timeout_s: float, interval_s: float):
        self.ip = ip or DEFAULT_PING_IP
        self.port = int(port) if port else DEFAULT_PING_PORT
        self.timeout_s = float(timeout_s) if timeout_s else DEFAULT_PING_TIMEOUT
        self.interval_s = float(interval_s) if interval_s else DEFAULT_PING_INTERVAL

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_ping",
            update_interval=timedelta(seconds=self.interval_s),
        )

    async def _async_update_data(self) -> dict:
        try:
            ok = await tcp_ping(self.ip, self.port, self.timeout_s)
            return {"ok": ok, "ip": self.ip, "port": self.port}
        except Exception as err:
            raise UpdateFailed(str(err)) from err
