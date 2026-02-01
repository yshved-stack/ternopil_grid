"""Sensors for the Ternopil Grid Schedule integration.

Fixes: ensure we pass the *DataUpdateCoordinator* instance to CoordinatorEntity.
Home Assistant stores multiple coordinators in hass.data[DOMAIN][entry_id] as a dict:
  {"schedule": <DataUpdateCoordinator>, "ping": <DataUpdateCoordinator>}

This platform uses the schedule coordinator.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Final

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN


# --- helpers ---


def _now(hass: HomeAssistant) -> datetime:
    """Return current time in HA's configured timezone."""
    return dt_util.now()


def _coordinator(hass: HomeAssistant, entry: ConfigEntry):
    """Return the schedule DataUpdateCoordinator for this config entry."""
    entry_bucket = hass.data[DOMAIN][entry.entry_id]
    # Newer versions store a dict: {"schedule": coord, "ping": coord}
    if isinstance(entry_bucket, dict):
        return entry_bucket.get("schedule") or entry_bucket.get("coordinator")
    # Backwards compatibility: some versions stored the coordinator directly
    return entry_bucket


def _segments(coord_data: Any) -> list[dict[str, Any]]:
    """Coordinator returns list[dict] segments."""
    if not coord_data:
        return []
    if isinstance(coord_data, list):
        return coord_data
    # defensive: some older versions might wrap in dict
    if isinstance(coord_data, dict) and "segments" in coord_data:
        return coord_data["segments"] or []
    return []


def _segment_at(segments: list[dict[str, Any]], ts_utc: float) -> dict[str, Any] | None:
    """Find segment that contains ts_utc."""
    for s in segments:
        try:
            start = float(s.get("start_ts"))
            end = float(s.get("end_ts"))
        except (TypeError, ValueError):
            continue
        if start <= ts_utc < end:
            return s
    return None


def _next_change_after(
    segments: list[dict[str, Any]], ts_utc: float
) -> tuple[datetime | None, str | None]:
    """Return (datetime_of_next_change_utc, next_color)."""
    current = _segment_at(segments, ts_utc)
    current_color = current.get("color") if current else None

    # iterate in order
    for s in segments:
        try:
            start = float(s.get("start_ts"))
        except (TypeError, ValueError):
            continue
        if start <= ts_utc:
            continue
        color = s.get("color")
        if color != current_color:
            return dt_util.utc_from_timestamp(start), color

    return None, None


def _minutes_off_on_date(hass: HomeAssistant, segments: list[dict[str, Any]], target_date: datetime.date) -> int:
    """Sum minutes where color == 'red' for the given local date."""
    tz = dt_util.DEFAULT_TIME_ZONE
    # local day's UTC bounds
    start_local = datetime.combine(target_date, datetime.min.time(), tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    start_utc = dt_util.as_utc(start_local)
    end_utc = dt_util.as_utc(end_local)

    total = 0.0
    for s in segments:
        if s.get("color") != "red":
            continue
        try:
            s0 = dt_util.utc_from_timestamp(float(s.get("start_ts")))
            s1 = dt_util.utc_from_timestamp(float(s.get("end_ts")))
        except (TypeError, ValueError):
            continue
        a = max(s0, start_utc)
        b = min(s1, end_utc)
        if b > a:
            total += (b - a).total_seconds() / 60.0

    return int(round(total))


# --- entities ---


@dataclass(frozen=True, kw_only=True)
class TGDescription(SensorEntityDescription):
    key: str


DESCRIPTIONS: Final[list[TGDescription]] = [
    TGDescription(key="countdown", name="Countdown"),
    TGDescription(key="next_change", name="Next change"),
    TGDescription(key="off_today", name="Off today"),
    TGDescription(key="off_tomorrow", name="Off tomorrow"),
    TGDescription(key="schedule_rolling_24h", name="Schedule rolling 24h"),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coord = _coordinator(hass, entry)

    entities: list[SensorEntity] = [
        TernopilGridSensor(hass, entry, coord, desc) for desc in DESCRIPTIONS
    ]

    async_add_entities(entities)


class TernopilGridSensor(CoordinatorEntity, SensorEntity):
    """Single sensor exposing derived info from the schedule coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator,
        description: TGDescription,
    ) -> None:
        super().__init__(coordinator)
        self.hass = hass
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        segs = _segments(self.coordinator.data)
        now_local = _now(self.hass)
        now_utc = dt_util.as_utc(now_local)
        ts_utc = now_utc.timestamp()

        key = self.entity_description.key

        if key == "countdown":
            next_dt_utc, _ = _next_change_after(segs, ts_utc)
            if not next_dt_utc:
                return None
            delta = next_dt_utc - now_utc
            if delta.total_seconds() < 0:
                return 0
            # seconds
            return int(delta.total_seconds())

        if key == "next_change":
            next_dt_utc, _ = _next_change_after(segs, ts_utc)
            if not next_dt_utc:
                return None
            # show in local tz
            return dt_util.as_local(next_dt_utc)

        if key == "off_today":
            return _minutes_off_on_date(self.hass, segs, now_local.date())

        if key == "off_tomorrow":
            return _minutes_off_on_date(self.hass, segs, (now_local + timedelta(days=1)).date())

        if key == "schedule_rolling_24h":
            # compact string of next 48 half-hours: R/Y/G
            window_end = now_utc + timedelta(hours=24)
            chars: list[str] = []
            # create lookup by start_ts for deterministic order
            for s in segs:
                try:
                    s0 = dt_util.utc_from_timestamp(float(s.get("start_ts")))
                except (TypeError, ValueError):
                    continue
                if not (now_utc <= s0 < window_end):
                    continue
                c = s.get("color")
                chars.append({"red": "R", "yellow": "Y", "green": "G"}.get(c, "?"))
            return "".join(chars) if chars else None

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        segs = _segments(self.coordinator.data)
        now_local = _now(self.hass)
        now_utc = dt_util.as_utc(now_local)
        current = _segment_at(segs, now_utc.timestamp())

        next_dt_utc, next_color = _next_change_after(segs, now_utc.timestamp())

        attrs: dict[str, Any] = {
            "current_color": current.get("color") if current else None,
            "current_start": dt_util.as_local(dt_util.utc_from_timestamp(current["start_ts"])) if current and current.get("start_ts") else None,
            "current_end": dt_util.as_local(dt_util.utc_from_timestamp(current["end_ts"])) if current and current.get("end_ts") else None,
            "next_change": dt_util.as_local(next_dt_utc) if next_dt_utc else None,
            "next_color": next_color,
        }

        # keep attributes small
        return attrs
