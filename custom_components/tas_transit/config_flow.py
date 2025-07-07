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
    CONF_DEPARTURE_REMINDER,
    CONF_EARLY_THRESHOLD,
    CONF_LATE_THRESHOLD,
    CONF_SCHEDULED_DEPARTURE_TIME,
    CONF_STOP_ID,
    CONF_STOP_NAME,
    CONF_STOPS,
    CONF_TIME_TO_GET_THERE,
    DEFAULT_DEPARTURE_REMINDER,
    DEFAULT_EARLY_THRESHOLD,
    DEFAULT_LATE_THRESHOLD,
    DEFAULT_TIME_TO_GET_THERE,
    DOMAIN,
    TRANSPORT_WEB_URL,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STOP_ID, description={"suggested_value": "7109023"}): str,
        vol.Required(CONF_SCHEDULED_DEPARTURE_TIME): str,
        vol.Optional(CONF_TIME_TO_GET_THERE, default=DEFAULT_TIME_TO_GET_THERE): cv.positive_int,
        vol.Optional(CONF_EARLY_THRESHOLD, default=DEFAULT_EARLY_THRESHOLD): cv.positive_int,
        vol.Optional(CONF_LATE_THRESHOLD, default=DEFAULT_LATE_THRESHOLD): cv.positive_int,
        vol.Optional(CONF_DEPARTURE_REMINDER, default=DEFAULT_DEPARTURE_REMINDER): cv.positive_int,
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
            "stop_finder_url": TRANSPORT_WEB_URL + "7109023",
            "instructions": "To find your stop ID, visit the Tasmanian Transport website, search for your stop, and copy the ID from the URL (e.g., 7109023 from .../#?stop=7109023)",
        }

        if user_input is not None:
            try:
                # Validate the stop ID and get stop information
                api = TasTransitApi()
                stop_info = await api.get_stop_info(user_input[CONF_STOP_ID])
                
                if not stop_info:
                    errors[CONF_STOP_ID] = "stop_not_found"
                else:
                    # Validate departure time format
                    try:
                        self._validate_time_format(user_input[CONF_SCHEDULED_DEPARTURE_TIME])
                    except ValueError:
                        errors[CONF_SCHEDULED_DEPARTURE_TIME] = "invalid_time_format"
                    
                    if not errors:
                        # Create the config entry with stop information
                        stop_name = stop_info.get("name", f"Stop {user_input[CONF_STOP_ID]}")
                        
                        return self.async_create_entry(
                            title=f"Bus from {stop_name}",
                            data={
                                CONF_STOPS: [{
                                    CONF_STOP_ID: user_input[CONF_STOP_ID],
                                    CONF_STOP_NAME: stop_name,
                                    CONF_SCHEDULED_DEPARTURE_TIME: user_input[CONF_SCHEDULED_DEPARTURE_TIME],
                                    CONF_TIME_TO_GET_THERE: user_input[CONF_TIME_TO_GET_THERE],
                                    CONF_EARLY_THRESHOLD: user_input[CONF_EARLY_THRESHOLD],
                                    CONF_LATE_THRESHOLD: user_input[CONF_LATE_THRESHOLD],
                                    CONF_DEPARTURE_REMINDER: user_input[CONF_DEPARTURE_REMINDER],
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
            "stop_finder_url": TRANSPORT_WEB_URL + "7109023",
            "instructions": "To find your stop ID, visit the Tasmanian Transport website, search for your stop, and copy the ID from the URL (e.g., 7109023 from .../#?stop=7109023)",
        }

        if user_input is not None:
            try:
                # Validate the stop ID and get stop information
                api = TasTransitApi()
                stop_info = await api.get_stop_info(user_input[CONF_STOP_ID])
                
                if not stop_info:
                    errors[CONF_STOP_ID] = "stop_not_found"
                else:
                    # Validate departure time format
                    try:
                        self._validate_time_format(user_input[CONF_SCHEDULED_DEPARTURE_TIME])
                    except ValueError:
                        errors[CONF_SCHEDULED_DEPARTURE_TIME] = "invalid_time_format"
                    
                    if not errors:
                        # Get existing config data
                        existing_config = self.hass.config_entries.async_entries(DOMAIN)[0]
                        existing_data = dict(existing_config.data)
                        
                        # Add new stop to existing stops
                        stop_name = stop_info.get("name", f"Stop {user_input[CONF_STOP_ID]}")
                        new_stop = {
                            CONF_STOP_ID: user_input[CONF_STOP_ID],
                            CONF_STOP_NAME: stop_name,
                            CONF_SCHEDULED_DEPARTURE_TIME: user_input[CONF_SCHEDULED_DEPARTURE_TIME],
                            CONF_TIME_TO_GET_THERE: user_input[CONF_TIME_TO_GET_THERE],
                            CONF_EARLY_THRESHOLD: user_input[CONF_EARLY_THRESHOLD],
                            CONF_LATE_THRESHOLD: user_input[CONF_LATE_THRESHOLD],
                            CONF_DEPARTURE_REMINDER: user_input[CONF_DEPARTURE_REMINDER],
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

    def _validate_time_format(self, time_str: str) -> None:
        """Validate time format (HH:MM)."""
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                raise ValueError("Invalid time format")
            
            hours = int(parts[0])
            minutes = int(parts[1])
            
            if not (0 <= hours <= 23) or not (0 <= minutes <= 59):
                raise ValueError("Invalid time range")
                
        except (ValueError, IndexError) as err:
            raise ValueError("Invalid time format") from err