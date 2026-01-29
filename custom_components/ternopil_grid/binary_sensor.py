from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import DOMAIN


class _BaseBinary(BinarySensorEntity):
    def __init__(self, entry, name: str, suggested_object_id: str, icon: str, device_class: str | None = None):
        self.entry = entry
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{suggested_object_id}"
        self._attr_suggested_object_id = suggested_object_id
        self._attr_icon = icon
        if device_class:
            self._attr_device_class = device_class

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="Ternopil Grid Schedule",
            manufacturer="Community",
            model="Power + Schedule",
        )


class TernopilGridPowerPing(_BaseBinary):
    # binary_sensor.ternopil_grid_power
    def __init__(self, entry, ping_coordinator):
        super().__init__(entry, "Power (ping)", "ternopil_grid_power", "mdi:power-plug", "power")
        self.ping = ping_coordinator

    @property
    def available(self):
        return self.ping.last_update_success

    @property
    def is_on(self):
        data = self.ping.data or {}
        return bool(data.get("ok"))

    async def async_added_to_hass(self):
        self.async_on_remove(self.ping.async_add_listener(self.async_write_ha_state))


class TernopilPlannedOutage(_BaseBinary):
    # binary_sensor.ternopil_grid_planned_outage
    def __init__(self, entry, schedule_coordinator):
        super().__init__(entry, "Planned outage", "ternopil_grid_planned_outage", "mdi:transmission-tower-off", "power")
        self.schedule = schedule_coordinator

    @property
    def available(self):
        return self.schedule.last_update_success

    @property
    def is_on(self):
        now = dt_util.utcnow().timestamp()
        for seg in self.schedule.data or []:
            if seg["start"] <= now < seg["end"]:
                return seg["color"] in ("red", "yellow")
        return False

    async def async_added_to_hass(self):
        self.async_on_remove(self.schedule.async_add_listener(self.async_write_ha_state))


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            TernopilGridPowerPing(entry, data["ping"]),
            TernopilPlannedOutage(entry, data["schedule"]),
        ],
        True,
    )
