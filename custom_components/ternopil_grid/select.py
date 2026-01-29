from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN, CONF_GROUP, DEFAULT_GROUP, GROUP_OPTIONS


class TernopilGroupSelect(SelectEntity):
    _attr_icon = "mdi:account-group"
    _attr_name = "Outage group"
    _attr_options = GROUP_OPTIONS

    def __init__(self, hass, entry):
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_ternopil_grid_group"
        self._attr_suggested_object_id = "ternopil_grid_group"

    @property
    def current_option(self):
        return self.entry.options.get(CONF_GROUP, self.entry.data.get(CONF_GROUP, DEFAULT_GROUP))

    async def async_select_option(self, option: str) -> None:
        self.hass.config_entries.async_update_entry(
            self.entry,
            options={**self.entry.options, CONF_GROUP: option},
        )
        await self.hass.config_entries.async_reload(self.entry.entry_id)

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="Ternopil Grid Schedule",
        )


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([TernopilGroupSelect(hass, entry)], True)
