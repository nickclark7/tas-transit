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
    CONF_ARRIVAL_DESTINATION,
    CONF_DEPARTURE_REMINDER,
    CONF_DEPARTURE_STOP_ID,
    CONF_DEPARTURE_STOP_NAME,
    CONF_EARLY_THRESHOLD,
    CONF_LATE_THRESHOLD,
    CONF_SCHEDULED_DEPARTURE_TIME,
    CONF_TIME_TO_GET_THERE,
    DEFAULT_DEPARTURE_REMINDER,
    DEFAULT_EARLY_THRESHOLD,
    DEFAULT_LATE_THRESHOLD,
    DEFAULT_TIME_TO_GET_THERE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEPARTURE_STOP_NAME): str,
        vol.Required(CONF_ARRIVAL_DESTINATION, default="Hobart"): str,
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

        if user_input is not None:
            try:
                # Validate the departure stop exists
                api = TasTransitApi()
                
                # Try to find the bus stop
                latitude = self.hass.config.latitude
                longitude = self.hass.config.longitude
                
                stops = await api.search_stops_by_location(
                    latitude, longitude, query=user_input[CONF_DEPARTURE_STOP_NAME]
                )
                
                if not stops:
                    errors["base"] = "stop_not_found"
                else:
                    # Find the best matching stop
                    stop = self._find_best_stop_match(
                        stops, user_input[CONF_DEPARTURE_STOP_NAME]
                    )
                    
                    if not stop:
                        errors["base"] = "stop_not_found"
                    else:
                        # Validate departure time format
                        try:
                            self._validate_time_format(user_input[CONF_SCHEDULED_DEPARTURE_TIME])
                        except ValueError:
                            errors[CONF_SCHEDULED_DEPARTURE_TIME] = "invalid_time_format"
                        
                        if not errors:
                            # Create the config entry
                            return self.async_create_entry(
                                title=f"Bus from {user_input[CONF_DEPARTURE_STOP_NAME]}",
                                data={
                                    CONF_DEPARTURE_STOP_ID: stop["id"],
                                    CONF_DEPARTURE_STOP_NAME: stop["name"],
                                    CONF_ARRIVAL_DESTINATION: user_input[CONF_ARRIVAL_DESTINATION],
                                    CONF_SCHEDULED_DEPARTURE_TIME: user_input[CONF_SCHEDULED_DEPARTURE_TIME],
                                    CONF_TIME_TO_GET_THERE: user_input[CONF_TIME_TO_GET_THERE],
                                    CONF_EARLY_THRESHOLD: user_input[CONF_EARLY_THRESHOLD],
                                    CONF_LATE_THRESHOLD: user_input[CONF_LATE_THRESHOLD],
                                    CONF_DEPARTURE_REMINDER: user_input[CONF_DEPARTURE_REMINDER],
                                },
                            )

            except Exception as exception:
                _LOGGER.exception("Unexpected exception: %s", exception)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    def _find_best_stop_match(self, stops: list[dict], query: str) -> dict | None:
        """Find the best matching stop from search results."""
        query_lower = query.lower()
        
        # First try exact match
        for stop in stops:
            if stop["name"].lower() == query_lower:
                return stop
        
        # Then try partial match
        for stop in stops:
            if query_lower in stop["name"].lower():
                return stop
        
        # Return first result if no good match
        return stops[0] if stops else None

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