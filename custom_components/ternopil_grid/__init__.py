from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_GROUP,
    CONF_PING_IP,
    CONF_PING_PORT,
    CONF_PING_TIMEOUT,
    CONF_PING_INTERVAL,
    DEFAULT_GROUP,
    DEFAULT_PING_IP,
    DEFAULT_PING_PORT,
    DEFAULT_PING_TIMEOUT,
    DEFAULT_PING_INTERVAL,
    PLATFORMS,
)
from .coordinator import TernopilScheduleCoordinator, TernopilPingCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    group = entry.options.get(CONF_GROUP, entry.data.get(CONF_GROUP, DEFAULT_GROUP))

    ping_ip = entry.options.get(CONF_PING_IP, entry.data.get(CONF_PING_IP, DEFAULT_PING_IP))
    ping_port = entry.options.get(CONF_PING_PORT, entry.data.get(CONF_PING_PORT, DEFAULT_PING_PORT))
    ping_timeout = entry.options.get(CONF_PING_TIMEOUT, entry.data.get(CONF_PING_TIMEOUT, DEFAULT_PING_TIMEOUT))
    ping_interval = entry.options.get(CONF_PING_INTERVAL, entry.data.get(CONF_PING_INTERVAL, DEFAULT_PING_INTERVAL))

    schedule = TernopilScheduleCoordinator(hass, group)
    await schedule.async_config_entry_first_refresh()

    ping = TernopilPingCoordinator(hass, ping_ip, ping_port, ping_timeout, ping_interval)
    await ping.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "entry": entry,
        "schedule": schedule,
        "ping": ping,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
