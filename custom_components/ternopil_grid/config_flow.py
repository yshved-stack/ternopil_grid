from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

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
    GROUP_OPTIONS,
)


class TernopilGridConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input:
            return self.async_create_entry(title="Ternopil Grid Schedule", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_GROUP, default=DEFAULT_GROUP): vol.In(GROUP_OPTIONS),
                vol.Required(CONF_PING_IP, default=DEFAULT_PING_IP): str,
                vol.Required(CONF_PING_PORT, default=DEFAULT_PING_PORT): int,
                vol.Required(CONF_PING_TIMEOUT, default=DEFAULT_PING_TIMEOUT): vol.Coerce(float),
                vol.Required(CONF_PING_INTERVAL, default=DEFAULT_PING_INTERVAL): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    def async_get_options_flow(config_entry):
        return TernopilGridOptionsFlow(config_entry)


class TernopilGridOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input:
            return self.async_create_entry(title="", data=user_input)

        cur = lambda k, d: self.entry.options.get(k, self.entry.data.get(k, d))

        schema = vol.Schema(
            {
                vol.Required(CONF_GROUP, default=cur(CONF_GROUP, DEFAULT_GROUP)): vol.In(GROUP_OPTIONS),
                vol.Required(CONF_PING_IP, default=cur(CONF_PING_IP, DEFAULT_PING_IP)): str,
                vol.Required(CONF_PING_PORT, default=cur(CONF_PING_PORT, DEFAULT_PING_PORT)): int,
                vol.Required(CONF_PING_TIMEOUT, default=cur(CONF_PING_TIMEOUT, DEFAULT_PING_TIMEOUT)): vol.Coerce(float),
                vol.Required(CONF_PING_INTERVAL, default=cur(CONF_PING_INTERVAL, DEFAULT_PING_INTERVAL)): vol.Coerce(float),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
