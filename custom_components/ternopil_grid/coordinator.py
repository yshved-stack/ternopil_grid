from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import fetch_schedule
from .const import (
    DOMAIN,
    CONF_CITY_ID,
    CONF_STREET_ID,
    CONF_GROUP,
    DEFAULT_TERNOPIL_CITY_ID,
    DEFAULT_UPDATE_INTERVAL,
)
from .ping import ping

_LOGGER = logging.getLogger(__name__)


def _val_to_color(v: str) -> str:
    # Observed upstream values: "0", "1", "10"
    # 0 = outage (red), 1 = power (green), 10 = limited/uncertain (yellow)
    if v == "0":
        return "red"
    if v == "1":
        return "green"
    return "yellow"


def _parse_day0(date_graph: datetime | None) -> datetime:
    if isinstance(date_graph, datetime):
        return date_graph.astimezone(timezone.utc).replace(microsecond=0)
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _times_to_segments(day0_utc: datetime, times: dict[str, str]) -> list[dict[str, Any]]:
    items: list[tuple[datetime, datetime, str]] = []
    for hhmm, v in times.items():
        try:
            hh, mm = hhmm.split(":")
            start = day0_utc.replace(hour=int(hh), minute=int(mm))
        except Exception:  # noqa: BLE001
            continue
        end = start + timedelta(minutes=30)
        items.append((start, end, _val_to_color(str(v))))

    items.sort(key=lambda x: x[0])

    segs: list[dict[str, Any]] = []
    for start, end, color in items:
        if not segs:
            segs.append({"start_ts": start.timestamp(), "end_ts": end.timestamp(), "color": color})
            continue
        last = segs[-1]
        if last["color"] == color and abs(last["end_ts"] - start.timestamp()) < 1:
            last["end_ts"] = end.timestamp()
        else:
            segs.append({"start_ts": start.timestamp(), "end_ts": end.timestamp(), "color": color})
    return segs


class TernopilScheduleCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Fetch and normalize the outage schedule into contiguous segments."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.city_id: int = int(entry.data.get(CONF_CITY_ID, DEFAULT_TERNOPIL_CITY_ID))
        self.street_id: int = int(entry.data[CONF_STREET_ID])
        self.group: str | None = entry.data.get(CONF_GROUP)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_schedule",
            update_interval=timedelta(seconds=DEFAULT_UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> list[dict[str, Any]]:
        if not self.group:
            raise UpdateFailed("Missing building group")

        try:
            result = await fetch_schedule(
                self.hass,
                city_id=self.city_id,
                street_id=self.street_id,
                group=self.group,
            )
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err

        times = result.get("times")
        raw = result.get("raw")
        empty = bool(result.get("empty"))

        if not isinstance(raw, dict):
            raise UpdateFailed("Upstream payload missing raw")

        # If upstream returned 200 but empty graph: allow setup by returning a short unknown segment.
        # This prevents config entry from being stuck in "Failed setup" when upstream is temporarily empty.
        if empty or not isinstance(times, dict) or len(times) == 0:
            now = datetime.now(timezone.utc).replace(microsecond=0)
            return [{"start_ts": now.timestamp(), "end_ts": (now + timedelta(minutes=30)).timestamp(), "color": "yellow"}]

        day0 = _parse_day0(result.get("date_graph"))
        segs = _times_to_segments(day0, {str(k): str(v) for k, v in times.items()})
        if not segs:
            _LOGGER.warning("Schedule empty, keeping previous state"); return []

        return segs


class TernopilPingCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Ping coordinator for simple connectivity/outage heuristics."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        *,
        ping_ip: str | None,
        ping_interval: int | None,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.ping_ip = ping_ip or "1.1.1.1"
        self._interval = int(ping_interval or 10)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_ping",
            update_interval=timedelta(seconds=self._interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            ok = await ping(self.ping_ip, timeout_s=1.0)
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(str(err)) from err
        return {"ok": bool(ok)}
