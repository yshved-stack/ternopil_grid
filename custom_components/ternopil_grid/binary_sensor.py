"""Binary sensors for Ternopil Grid integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def _utc_ts_now() -> float:
    return datetime.now(timezone.utc).timestamp()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensors from a config entry."""

    data: Any = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    schedule = None
    ping = None

    if isinstance(data, dict):
        schedule = data.get("schedule")
        ping = data.get("ping")

    # Backwards compatibility: if integrations stored coordinator directly.
    if schedule is None and hasattr(data, "async_add_listener"):
        schedule = data

    entities: list[BinarySensorEntity] = []

    if schedule is not None:
        entities.append(TernopilPlannedOutageBinarySensor(schedule, entry))

    if ping is not None:
        entities.append(TernopilPowerPingBinarySensor(ping, entry))

    if not entities:
        _LOGGER.warning("No coordinators found in hass.data for entry %s", entry.entry_id)
        return

    async_add_entities(entities)


@dataclass(frozen=True)
class _BsDesc:
    key: str
    name: str


class _BaseTernopilBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Base binary sensor backed by a DataUpdateCoordinator."""

    _desc: _BsDesc

    def __init__(self, coordinator, entry: ConfigEntry, desc: _BsDesc) -> None:
        super().__init__(coordinator)
        self._desc = desc
        self._entry_id = entry.entry_id

        self._attr_name = desc.name
        self._attr_unique_id = f"{entry.entry_id}_{desc.key}"

    @property
    def available(self) -> bool:
        return super().available


class TernopilPlannedOutageBinarySensor(_BaseTernopilBinarySensor):
    """True when current half-hour segment is marked as outage."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, _BsDesc("planned_outage", "Planned outage"))

    @property
    def is_on(self) -> bool:
        now = _utc_ts_now()
        segments = self.coordinator.data
        if not isinstance(segments, list):
            return False

        for seg in segments:
            if not isinstance(seg, dict):
                continue
            start = seg.get("start")
            end = seg.get("end")
            if start is None or end is None:
                continue
            try:
                if float(start) <= now < float(end):
                    color = str(seg.get("color", "")).lower()
                    # In this integration: red = outage, yellow = limited/uncertain.
                    return color == "red"
            except Exception:
                continue
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        now = _utc_ts_now()
        segments = self.coordinator.data
        if not isinstance(segments, list):
            return {}

        current = None
        for seg in segments:
            if not isinstance(seg, dict):
                continue
            try:
                if float(seg.get("start", -1)) <= now < float(seg.get("end", -1)):
                    current = seg
                    break
            except Exception:
                continue

        if not current:
            return {}

        return {
            "color": current.get("color"),
            "segment_start": current.get("start"),
            "segment_end": current.get("end"),
        }


class TernopilPowerPingBinarySensor(_BaseTernopilBinarySensor):
    """True when ping coordinator reports connectivity (power present)."""

    def __init__(self, coordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, _BsDesc("power_ping", "Power ping"))

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data
        if isinstance(data, dict):
            return bool(data.get("ok"))
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        if not isinstance(data, dict):
            return {}
        return {
            "ip": data.get("ip"),
            "port": data.get("port"),
            "method": data.get("method"),
        }
