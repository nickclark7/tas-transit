"""Config flow for Tasmanian Transport integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .api import TasTransitApi
from .const import (
    CONF_STOP_ID,
    CONF_STOP_NAME,
    CONF_STOPS,
    DOMAIN,
    TRANSPORT_WEB_URL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STOP_ID, description={"suggested_value": "7109023"}): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tasmanian Transport."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        description_placeholders = {
            "transport_site_url": TRANSPORT_WEB_URL,
            "stop_finder_url": TRANSPORT_WEB_URL + "7109023",
            "instructions": "Stop IDs consist of your postcode followed by three digits (e.g., 7109023 for postcode 7109). To find your stop ID, visit the Tasmanian Transport website, search for your stop, and copy the ID from the URL.",
        }

        if user_input is not None:
            try:
                # Validate the stop ID and get stop information
                api = TasTransitApi()
                stop_info = await api.get_stop_info(user_input[CONF_STOP_ID])
                
                if not stop_info:
                    errors[CONF_STOP_ID] = "stop_not_found"
                else:
                    # Extract stop name from the API response
                    stop_name = "Unknown Stop"
                    if "stop" in stop_info and "name" in stop_info["stop"]:
                        stop_name = stop_info["stop"]["name"]
                    elif "name" in stop_info:
                        stop_name = stop_info["name"]
                    else:
                        stop_name = f"Stop {user_input[CONF_STOP_ID]}"
                    
                    return self.async_create_entry(
                        title=f"Bus from {stop_name}",
                        data={
                            CONF_STOPS: [{
                                CONF_STOP_ID: user_input[CONF_STOP_ID],
                                CONF_STOP_NAME: stop_name,
                            }],
                        },
                    )

            except Exception as exception:
                _LOGGER.exception("Unexpected exception: %s", exception)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_add_stop(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding an additional stop."""
        errors: dict[str, str] = {}
        description_placeholders = {
            "transport_site_url": TRANSPORT_WEB_URL,
            "stop_finder_url": TRANSPORT_WEB_URL + "7109023",
            "instructions": "Stop IDs consist of your postcode followed by three digits (e.g., 7109023 for postcode 7109). To find your stop ID, visit the Tasmanian Transport website, search for your stop, and copy the ID from the URL.",
        }

        if user_input is not None:
            try:
                # Validate the stop ID and get stop information
                api = TasTransitApi()
                stop_info = await api.get_stop_info(user_input[CONF_STOP_ID])
                
                if not stop_info:
                    errors[CONF_STOP_ID] = "stop_not_found"
                else:
                    # Get existing config data
                    existing_config = self.hass.config_entries.async_entries(DOMAIN)[0]
                    existing_data = dict(existing_config.data)
                    
                    # Extract stop name from the API response  
                    stop_name = "Unknown Stop"
                    if "stop" in stop_info and "name" in stop_info["stop"]:
                        stop_name = stop_info["stop"]["name"]
                    elif "name" in stop_info:
                        stop_name = stop_info["name"]
                    else:
                        stop_name = f"Stop {user_input[CONF_STOP_ID]}"
                    
                    new_stop = {
                        CONF_STOP_ID: user_input[CONF_STOP_ID],
                        CONF_STOP_NAME: stop_name,
                    }
                    
                    existing_data[CONF_STOPS].append(new_stop)
                    
                    # Update the config entry
                    self.hass.config_entries.async_update_entry(
                        existing_config,
                        data=existing_data,
                    )
                    
                    return self.async_create_entry(
                        title=f"Added stop: {stop_name}",
                        data=existing_data,
                    )

            except Exception as exception:
                _LOGGER.exception("Unexpected exception: %s", exception)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="add_stop",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders=description_placeholders,
        )

