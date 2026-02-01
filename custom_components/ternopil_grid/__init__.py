from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_PING_IP, CONF_PING_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Lazy imports: keep config_flow import safe
    from .coordinator import TernopilScheduleCoordinator, TernopilPingCoordinator

    hass.data.setdefault(DOMAIN, {})

    schedule = TernopilScheduleCoordinator(hass, entry)
    ping = TernopilPingCoordinator(
        hass,
        entry,
        ping_ip=entry.options.get(CONF_PING_IP, entry.data.get(CONF_PING_IP)),
        ping_interval=entry.options.get(CONF_PING_INTERVAL, entry.data.get(CONF_PING_INTERVAL)),
    )

    # Store coordinators even if upstream is flaky (don’t fail setup)
    hass.data[DOMAIN][entry.entry_id] = {"schedule": schedule, "ping": ping}

    # Forward platforms first so UI entities exist even if first refresh fails
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Kick off refreshes (non-fatal)
    async def _refresh_safe(coordinator, name: str) -> None:
        try:
            await coordinator.async_config_entry_first_refresh()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("%s first refresh failed (non-fatal): %s", name, err)

    hass.async_create_task(_refresh_safe(schedule, "schedule"))
    hass.async_create_task(_refresh_safe(ping, "ping"))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
