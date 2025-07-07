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
    BUS_STATUS_CANCELLED,
    BUS_STATUS_EARLY,
    BUS_STATUS_LATE,
    BUS_STATUS_ON_TIME,
    BUS_STATUS_UNKNOWN,
    CONF_EARLY_THRESHOLD,
    CONF_LATE_THRESHOLD,
    CONF_SCHEDULED_DEPARTURE_TIME,
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
                processed_data = self._process_departures(departures, stop_config)
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

    def _process_departures(self, departures: list[dict[str, Any]], stop_config: dict[str, Any]) -> dict[str, Any]:
        """Process departure data and calculate bus status."""
        now = datetime.now()
        
        # Filter departures to only include upcoming ones
        upcoming_departures = []
        for departure in departures:
            scheduled_time = self._get_scheduled_time(departure)
            if scheduled_time and scheduled_time > now:
                upcoming_departures.append(departure)
        
        # Sort by scheduled departure time
        upcoming_departures.sort(key=lambda x: self._get_scheduled_time(x) or datetime.max)
        
        # Get the next departure
        next_departure = upcoming_departures[0] if upcoming_departures else None
        
        if not next_departure:
            return {
                "next_departure": None,
                "bus_status": BUS_STATUS_UNKNOWN,
                "time_to_departure": None,
                "departures": [],
                "last_updated": now,
                "stop_config": stop_config,
            }
        
        # Calculate bus status
        bus_status = self._calculate_bus_status(next_departure, stop_config)
        
        # Calculate time to departure
        scheduled_time = self._get_scheduled_time(next_departure)
        time_to_departure = None
        if scheduled_time:
            time_to_departure = int((scheduled_time - now).total_seconds() / 60)
        
        return {
            "next_departure": next_departure,
            "bus_status": bus_status,
            "time_to_departure": time_to_departure,
            "departures": upcoming_departures[:5],  # Keep top 5 departures
            "last_updated": now,
            "stop_config": stop_config,
        }

    def _get_scheduled_time(self, departure: dict[str, Any]) -> datetime | None:
        """Extract scheduled departure time from departure data."""
        # Try different possible field names for scheduled time
        time_fields = [
            "scheduledArrivalTime",
            "scheduledDepartureTime",
            "scheduled_arrival_time",
            "scheduled_departure_time",
            "departureTime",
            "arrivalTime",
        ]
        
        for field in time_fields:
            if field in departure:
                return self.api.parse_departure_time(departure[field])
        
        return None

    def _get_estimated_time(self, departure: dict[str, Any]) -> datetime | None:
        """Extract estimated departure time from departure data."""
        # Try different possible field names for estimated time
        time_fields = [
            "estimatedDepartureTime",
            "estimatedArrivalTime",
            "estimated_departure_time",
            "estimated_arrival_time",
            "realTimeDepartureTime",
            "realTimeArrivalTime",
        ]
        
        for field in time_fields:
            if field in departure and departure[field]:
                return self.api.parse_departure_time(departure[field])
        
        return None

    def _calculate_bus_status(self, departure: dict[str, Any], stop_config: dict[str, Any]) -> str:
        """Calculate bus status based on scheduled vs estimated time."""
        scheduled_time = self._get_scheduled_time(departure)
        estimated_time = self._get_estimated_time(departure)
        
        if not scheduled_time:
            return BUS_STATUS_UNKNOWN
        
        # Check if bus is cancelled
        if "cancelled" in departure and departure["cancelled"]:
            return BUS_STATUS_CANCELLED
        
        # If no estimated time, assume on time
        if not estimated_time:
            return BUS_STATUS_ON_TIME
        
        # Calculate difference in minutes
        diff_minutes = (estimated_time - scheduled_time).total_seconds() / 60
        
        early_threshold = stop_config[CONF_EARLY_THRESHOLD]
        late_threshold = stop_config[CONF_LATE_THRESHOLD]
        
        if diff_minutes < -early_threshold:
            return BUS_STATUS_EARLY
        elif diff_minutes > late_threshold:
            return BUS_STATUS_LATE
        else:
            return BUS_STATUS_ON_TIME

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