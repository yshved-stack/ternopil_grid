from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import DOMAIN


@dataclass(frozen=True, kw_only=True)
class TGDBinaryDescription(BinarySensorEntityDescription):
    key: str


POWER_PING = TGDBinaryDescription(
    key="power_ping",
    name="Power (ping)",
    icon="mdi:power-plug",
    device_class="power",
)

PLANNED_OUTAGE = TGDBinaryDescription(
    key="planned_outage",
    name="Planned outage",
    icon="mdi:transmission-tower-off",
    device_class="power",
)


class TernopilGridBinary(BinarySensorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry, description: TGDBinaryDescription, coordinator):
        self.entity_description = description
        self.entry = entry
        self.coordinator = coordinator

        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="Ternopil Grid Schedule",
            manufacturer="Community",
            model="Power + Schedule",
        )

    @property
    def available(self):
        return self.coordinator.last_update_success


class TernopilGridPowerPing(TernopilGridBinary):
    def __init__(self, entry, ping_coordinator):
        super().__init__(entry, POWER_PING, ping_coordinator)

    @property
    def is_on(self):
        data = self.coordinator.data or {}
        return bool(data.get("ok"))

    async def async_added_to_hass(self):
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))


class TernopilPlannedOutage(TernopilGridBinary):
    def __init__(self, entry, schedule_coordinator):
        super().__init__(entry, PLANNED_OUTAGE, schedule_coordinator)

    @property
    def is_on(self):
        now = dt_util.utcnow().timestamp()
        for seg in self.coordinator.data or []:
            if seg["start"] <= now < seg["end"]:
                return seg["color"] in ("red", "yellow")
        return False

    async def async_added_to_hass(self):
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TernopilGridPowerPing(entry, data["ping"]),
            TernopilPlannedOutage(entry, data["schedule"]),
        ],
        True,
    )
