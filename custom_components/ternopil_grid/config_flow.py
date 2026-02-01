"""Config flow for Ternopil Grid.

UX goal (per user request):
 - No city selection (only Ternopil).
 - No group selection.
 - User searches a street by name (dropdown supports typing/search).
 - User enters house number (stored for display).
 - Integration resolves the group automatically via API.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

from .api import fetch_building_groups, fetch_streets
from .const import (
    DEFAULT_POWER_SENSOR_NAME,
    DEFAULT_TERNOPIL_CITY_ID,
    DOMAIN,
    CONF_CITY_ID,
    CONF_GROUP,
    CONF_HOUSE_NUMBER,
    CONF_STREET_ID,
    CONF_STREET_NAME,
    CONF_POWER_SENSOR_NAME,
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        # Load all streets once (Ternopil only). HA dropdown supports typing to filter.
        try:
            streets = await fetch_streets(self.hass, DEFAULT_TERNOPIL_CITY_ID)
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Street lookup failed: %s", err)
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_POWER_SENSOR_NAME, default=DEFAULT_POWER_SENSOR_NAME): str,
                }),
                errors={"base": "cannot_connect"},
            )

        # Build options as label/value pairs.
        options = [
            selector.SelectOptionDict(label=s["name"], value=str(s["id"]))
            for s in streets
        ]

        schema = vol.Schema(
            {
                vol.Required(CONF_STREET_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        sort=True,
                    )
                ),
                vol.Required(CONF_HOUSE_NUMBER): str,
                vol.Optional(CONF_POWER_SENSOR_NAME, default=DEFAULT_POWER_SENSOR_NAME): str,
            }
        )

        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

        # Resolve street
        street_id = int(user_input[CONF_STREET_ID])
        street_name = next((s["name"] for s in streets if s["id"] == street_id), str(street_id))
        house_number = str(user_input[CONF_HOUSE_NUMBER]).strip()

        # Resolve group automatically
        try:
            groups = await fetch_building_groups(
                self.hass, city_id=DEFAULT_TERNOPIL_CITY_ID, street_id=street_id
            )
            group = groups[0]
        except Exception as err:  # noqa: BLE001
            _LOGGER.exception("Group lookup failed: %s", err)
            errors["base"] = "cannot_connect"
            return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

        title = f"{street_name}, {house_number} (гр. {group})"

        data = {
            CONF_CITY_ID: DEFAULT_TERNOPIL_CITY_ID,
            CONF_STREET_ID: street_id,
            CONF_STREET_NAME: street_name,
            CONF_HOUSE_NUMBER: house_number,
            CONF_GROUP: group,
            CONF_POWER_SENSOR_NAME: user_input.get(CONF_POWER_SENSOR_NAME, DEFAULT_POWER_SENSOR_NAME),
        }

        return self.async_create_entry(title=title, data=data)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """No options currently. Placeholder to keep HA happy."""

    async def async_step_init(self, user_input=None):  # noqa: D401
        return self.async_create_entry(title="", data={})


async def async_get_options_flow(config_entry):
    return OptionsFlowHandler()
