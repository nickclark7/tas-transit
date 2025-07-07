"""Data update coordinator for Tasmanian Transport integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TasTransitApi, TasTransitApiError
from .const import (
    BUS_STATUS_CANCELLED,
    BUS_STATUS_EARLY,
    BUS_STATUS_LATE,
    BUS_STATUS_ON_TIME,
    BUS_STATUS_UNKNOWN,
    CONF_DEPARTURE_STOP_ID,
    CONF_EARLY_THRESHOLD,
    CONF_LATE_THRESHOLD,
    CONF_SCHEDULED_DEPARTURE_TIME,
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

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            stop_id = self.config_entry.data[CONF_DEPARTURE_STOP_ID]
            departures = await self.api.get_stop_departures(stop_id)
            
            # Process the departures data
            processed_data = self._process_departures(departures)
            
            return processed_data

        except TasTransitApiError as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _process_departures(self, departures: list[dict[str, Any]]) -> dict[str, Any]:
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
            }
        
        # Calculate bus status
        bus_status = self._calculate_bus_status(next_departure)
        
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

    def _calculate_bus_status(self, departure: dict[str, Any]) -> str:
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
        
        early_threshold = self.config_entry.data[CONF_EARLY_THRESHOLD]
        late_threshold = self.config_entry.data[CONF_LATE_THRESHOLD]
        
        if diff_minutes < -early_threshold:
            return BUS_STATUS_EARLY
        elif diff_minutes > late_threshold:
            return BUS_STATUS_LATE
        else:
            return BUS_STATUS_ON_TIME

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self.api.close()