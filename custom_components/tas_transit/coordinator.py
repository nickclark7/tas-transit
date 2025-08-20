"""Data update coordinator for Tasmanian Transport integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TasTransitApi, TasTransitApiError
from .const import (
    CONF_STOP_ID,
    CONF_STOPS,
    UPDATE_INTERVAL_DEFAULT,
    UPDATE_INTERVAL_FREQUENT,
    UPDATE_INTERVAL_THRESHOLD,
)

_LOGGER = logging.getLogger(__name__)


class TasTransitDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the Tasmanian Transport API."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        name: str,
        update_interval: timedelta,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=logger,
            name=name,
            update_interval=update_interval,
        )
        self.config_entry = config_entry
        self.api = TasTransitApi()
        self._next_update_call = None
        self._current_interval = UPDATE_INTERVAL_DEFAULT

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            stops_data = {}
            min_time_to_departure = None
            
            # Process each configured stop
            for stop_config in self.config_entry.data[CONF_STOPS]:
                stop_id = stop_config[CONF_STOP_ID]
                departures = await self.api.get_stop_departures(stop_id)
                
                # Process the departures data for this stop
                processed_data = self._process_departures(departures)
                stops_data[stop_id] = processed_data
                
                # Track the earliest departure across all stops
                time_to_departure = processed_data.get("time_to_departure")
                if time_to_departure is not None:
                    if min_time_to_departure is None or time_to_departure < min_time_to_departure:
                        min_time_to_departure = time_to_departure
            
            # Schedule next update based on closest departure
            await self._schedule_next_update(min_time_to_departure)
            
            return stops_data

        except TasTransitApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _process_departures(self, departures: list[dict[str, Any]]) -> dict[str, Any]:
        """Process departure data."""
        now = datetime.now()
        
        # Filter departures to only include upcoming ones (non-cancelled, positive minutes)
        upcoming_departures = []
        for departure in departures:
            # Use estimated minutes if available, otherwise scheduled minutes
            minutes_until = departure.get("estimatedMinutesUntilDeparture")
            if minutes_until is None:
                minutes_until = departure.get("scheduledMinutesUntilDeparture")
            
            # Include if not cancelled and has future departure time
            if not departure.get("cancelled", False) and minutes_until is not None and minutes_until >= 0:
                upcoming_departures.append(departure)
        
        # Sort by minutes until departure (estimated or scheduled)
        def sort_key(dep):
            est_min = dep.get("estimatedMinutesUntilDeparture")
            if est_min is not None:
                return est_min
            return dep.get("scheduledMinutesUntilDeparture", 999999)
        
        upcoming_departures.sort(key=sort_key)
        
        # Get the next departure
        next_departure = upcoming_departures[0] if upcoming_departures else None
        
        if not next_departure:
            return {
                "next_departure": None,
                "time_to_departure": None,
                "departures": [],
                "last_updated": now,
            }
        
        # Get time to departure (prefer estimated over scheduled)
        time_to_departure = next_departure.get("estimatedMinutesUntilDeparture")
        if time_to_departure is None:
            time_to_departure = next_departure.get("scheduledMinutesUntilDeparture")
        
        return {
            "next_departure": next_departure,
            "time_to_departure": time_to_departure,
            "departures": upcoming_departures,  # Expose all departures for user filtering
            "last_updated": now,
        }

    def _get_scheduled_time(self, departure: dict[str, Any]) -> datetime | None:
        """Extract scheduled departure time from departure data."""
        scheduled_time = departure.get("scheduledDepartureTime")
        if scheduled_time:
            return self.api.parse_departure_time(scheduled_time)
        return None

    def _get_estimated_time(self, departure: dict[str, Any]) -> datetime | None:
        """Extract estimated departure time from departure data."""
        estimated_time = departure.get("estimatedDepartureTime")
        if estimated_time:
            return self.api.parse_departure_time(estimated_time)
        return None


    async def _schedule_next_update(self, min_time_to_departure: int | None) -> None:
        """Schedule the next update based on departure times."""
        # Cancel any existing scheduled update
        if self._next_update_call:
            self._next_update_call()
            self._next_update_call = None
        
        # Determine update interval based on closest departure
        if min_time_to_departure is not None and min_time_to_departure <= UPDATE_INTERVAL_THRESHOLD:
            # Bus within threshold - use frequent updates
            interval = UPDATE_INTERVAL_FREQUENT
            self.logger.debug(
                "Bus departure in %d minutes, using %d second updates",
                min_time_to_departure,
                interval
            )
        else:
            # No buses soon - use default interval
            interval = UPDATE_INTERVAL_DEFAULT
            self.logger.debug(
                "No buses within %d minutes, using %d second updates",
                UPDATE_INTERVAL_THRESHOLD,
                interval
            )
        
        # Only reschedule if interval changed
        if interval != self._current_interval:
            self._current_interval = interval
            self.update_interval = timedelta(seconds=interval)
            
            # Schedule immediate update with new interval
            self._next_update_call = async_call_later(
                self.hass,
                interval,
                self._handle_refresh_interval
            )
    
    @callback
    async def _handle_refresh_interval(self, _now) -> None:
        """Handle the refresh interval callback."""
        self._next_update_call = None
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        # Cancel any pending update
        if self._next_update_call:
            self._next_update_call()
            self._next_update_call = None
        
        await self.api.close()