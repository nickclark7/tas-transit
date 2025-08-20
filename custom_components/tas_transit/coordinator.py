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
    CONF_DESTINATION_FILTERS,
    CONF_FILTER_MODE,
    CONF_LINE_FILTERS,
    CONF_STOP_ID,
    CONF_STOPS,
    FILTER_MODE_EXCLUDE,
    FILTER_MODE_INCLUDE,
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
        self._current_interval = UPDATE_INTERVAL_DEFAULT

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            stops_data = {}
            min_time_to_departure = None
            
            # Process each configured stop
            for stop_config in self.config_entry.data[CONF_STOPS]:
                stop_id = stop_config[CONF_STOP_ID]
                _LOGGER.debug("Fetching departures for stop %s", stop_id)
                departures = await self.api.get_stop_departures(stop_id)
                _LOGGER.debug("Received %d departures for stop %s", len(departures), stop_id)
                
                # Process the departures data for this stop with filters
                processed_data = self._process_departures(departures, stop_config)
                stops_data[stop_id] = processed_data
                _LOGGER.debug("Processed data for stop %s: next_departure=%s, time_to_departure=%s", 
                             stop_id, processed_data.get("next_departure") is not None, processed_data.get("time_to_departure"))
                
                # Track the earliest departure across all stops
                time_to_departure = processed_data.get("time_to_departure")
                if time_to_departure is not None:
                    if min_time_to_departure is None or time_to_departure < min_time_to_departure:
                        min_time_to_departure = time_to_departure
            
            # Schedule next update based on closest departure
            await self._schedule_next_update(min_time_to_departure)
            
            return stops_data

        except TasTransitApiError as err:
            _LOGGER.error("API error: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _apply_filters(self, departures: list[dict[str, Any]], stop_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Apply line number and destination filters to departures."""
        line_filters = stop_config.get(CONF_LINE_FILTERS, [])
        destination_filters = stop_config.get(CONF_DESTINATION_FILTERS, [])
        filter_mode = stop_config.get(CONF_FILTER_MODE, FILTER_MODE_INCLUDE)
        
        # If no filters configured, return all departures
        if not line_filters and not destination_filters:
            return departures
        
        filtered_departures = []
        
        for departure in departures:
            line_number = departure.get("lineNumber", "").strip()
            destination = departure.get("destinationName", "").strip()
            
            # Check if departure matches filters
            line_match = self._matches_line_filter(line_number, line_filters)
            destination_match = self._matches_destination_filter(destination, destination_filters)
            
            # Determine if departure should be included
            if filter_mode == FILTER_MODE_INCLUDE:
                # Include if matches any line filter OR any destination filter (when filters are provided)
                should_include = False
                if line_filters and line_match:
                    should_include = True
                if destination_filters and destination_match:
                    should_include = True
                # If only one type of filter is configured, only check that type
                if line_filters and not destination_filters:
                    should_include = line_match
                elif destination_filters and not line_filters:
                    should_include = destination_match
            else:  # FILTER_MODE_EXCLUDE
                # Exclude if matches any line filter OR any destination filter
                should_exclude = False
                if line_filters and line_match:
                    should_exclude = True
                if destination_filters and destination_match:
                    should_exclude = True
                should_include = not should_exclude
            
            if should_include:
                filtered_departures.append(departure)
                _LOGGER.debug("Including departure: line=%s, dest=%s", line_number, destination)
            else:
                _LOGGER.debug("Filtering out departure: line=%s, dest=%s", line_number, destination)
        
        return filtered_departures

    def _matches_line_filter(self, line_number: str, line_filters: list[str]) -> bool:
        """Check if line number matches any of the line filters."""
        if not line_filters:
            return False
        
        line_number_lower = line_number.lower()
        for filter_line in line_filters:
            filter_line_lower = filter_line.strip().lower()
            # Exact match or partial match (e.g., "58" matches "X58")
            if (line_number_lower == filter_line_lower or 
                filter_line_lower in line_number_lower or
                line_number_lower in filter_line_lower):
                return True
        return False

    def _matches_destination_filter(self, destination: str, destination_filters: list[str]) -> bool:
        """Check if destination matches any of the destination filters."""
        if not destination_filters:
            return False
        
        destination_lower = destination.lower()
        for filter_dest in destination_filters:
            filter_dest_lower = filter_dest.strip().lower()
            # Case-insensitive partial match
            if filter_dest_lower in destination_lower:
                return True
        return False

    def _process_departures(self, departures: list[dict[str, Any]], stop_config: dict[str, Any]) -> dict[str, Any]:
        """Process departure data with optional filtering."""
        now = datetime.now()
        
        _LOGGER.debug("Processing %d raw departures", len(departures))
        
        # Apply filters if configured
        filtered_departures = self._apply_filters(departures, stop_config)
        _LOGGER.debug("After filtering: %d departures remaining", len(filtered_departures))
        
        # Filter departures to only include upcoming ones (non-cancelled, positive minutes)
        upcoming_departures = []
        for departure in filtered_departures:
            # Use estimated minutes if available, otherwise scheduled minutes
            minutes_until = departure.get("estimatedMinutesUntilDeparture")
            if minutes_until is None:
                minutes_until = departure.get("scheduledMinutesUntilDeparture")
            
            cancelled = departure.get("cancelled", False)
            _LOGGER.debug("Departure: line=%s, dest=%s, minutes_until=%s, cancelled=%s", 
                         departure.get("lineNumber"), departure.get("destinationName"), minutes_until, cancelled)
            
            # Include if not cancelled and has future departure time
            if not cancelled and minutes_until is not None and minutes_until >= 0:
                upcoming_departures.append(departure)
        
        _LOGGER.debug("Found %d upcoming departures after filtering", len(upcoming_departures))
        
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
            _LOGGER.debug("No upcoming departures found")
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
        
        _LOGGER.debug("Next departure: line=%s, dest=%s, time_to_departure=%s", 
                     next_departure.get("lineNumber"), next_departure.get("destinationName"), time_to_departure)
        
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
        """Adjust update interval based on departure times."""
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
        
        # Update interval if changed - coordinator will handle the actual scheduling
        if interval != self._current_interval:
            self._current_interval = interval
            self.update_interval = timedelta(seconds=interval)
            self.logger.debug("Updated coordinator interval to %d seconds", interval)
    
    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        await self.api.close()