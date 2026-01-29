from __future__ import annotations

from .const import (
    CONF_GROUP,
    CONF_PING_IP,
    CONF_PING_PORT,
    CONF_PING_TIMEOUT,
    CONF_PING_INTERVAL,
)


async def async_get_config_entry_diagnostics(hass, entry):
    def get(k):
        return entry.options.get(k, entry.data.get(k))

    return {
        "group": get(CONF_GROUP),
        "ping_ip": get(CONF_PING_IP),
        "ping_port": get(CONF_PING_PORT),
        "ping_timeout": get(CONF_PING_TIMEOUT),
        "ping_interval": get(CONF_PING_INTERVAL),
    }
