"""API client for Tasmanian Transport."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp
import async_timeout

from .const import API_BASE_URL, API_STOPS_SEARCH, API_STOPDISPLAYS, API_TIMEOUT
from .exceptions import TasTransitApiException

_LOGGER = logging.getLogger(__name__)


class TasTransitApiError(TasTransitApiException):
    """Exception to indicate a general API error."""


class TasTransitApiTimeoutError(TasTransitApiError):
    """Exception to indicate API timeout."""


class TasTransitApiConnectionError(TasTransitApiError):
    """Exception to indicate API connection error."""


class TasTransitApi:
    """API client for Tasmanian Transport system."""

    def __init__(self) -> None:
        """Initialize the API client."""
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_stop_info(self, stop_id: str) -> dict[str, Any] | None:
        """Get stop display information including departures."""
        stop_url = f"{API_STOPDISPLAYS}/{stop_id}"
        
        try:
            session = await self._get_session()
            async with async_timeout.timeout(API_TIMEOUT):
                async with session.get(stop_url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    return data

        except asyncio.TimeoutError as err:
            raise TasTransitApiTimeoutError(f"Timeout while getting stop info for {stop_id}") from err
        except aiohttp.ClientError as err:
            raise TasTransitApiConnectionError(f"Connection error: {err}") from err
        except Exception as err:
            raise TasTransitApiError(f"Unexpected error: {err}") from err

    async def search_stops_by_location(
        self,
        latitude: float,
        longitude: float,
        query: str | None = None,
        radius: int = 1000,
    ) -> list[dict[str, Any]]:
        """Search for bus stops by location."""
        params = {
            "latitude": latitude,
            "longitude": longitude,
        }
        
        if query:
            params["query"] = query
        
        if radius != 1000:
            params["radius"] = radius

        try:
            session = await self._get_session()
            async with async_timeout.timeout(API_TIMEOUT):
                async with session.get(API_STOPS_SEARCH, params=params) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # The API returns a list of stops
                    if isinstance(data, list):
                        return data
                    else:
                        _LOGGER.warning("Unexpected API response format: %s", data)
                        return []

        except asyncio.TimeoutError as err:
            raise TasTransitApiTimeoutError("Timeout while searching for stops") from err
        except aiohttp.ClientError as err:
            raise TasTransitApiConnectionError(f"Connection error: {err}") from err
        except Exception as err:
            raise TasTransitApiError(f"Unexpected error: {err}") from err

    async def get_stop_departures(self, stop_id: str) -> list[dict[str, Any]]:
        """Get departure information for a specific stop."""
        departure_url = f"{API_STOPDISPLAYS}/{stop_id}"
        
        try:
            session = await self._get_session()
            async with async_timeout.timeout(API_TIMEOUT):
                async with session.get(departure_url) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Extract and flatten departures from nextStopVisits
                    departures = []
                    if isinstance(data, dict) and "nextStopVisits" in data:
                        for route_group in data["nextStopVisits"]:
                            direction = route_group.get("directionOfLine", {})
                            line_number = direction.get("lineNumber", "Unknown")
                            destination = direction.get("destinationName", "Unknown")
                            
                            for visit in route_group.get("stopVisits", []):
                                # Create a flattened departure object
                                departure = {
                                    "lineNumber": line_number,
                                    "destinationName": destination,
                                    "scheduledDepartureTime": visit.get("scheduledDepartureTime"),
                                    "estimatedDepartureTime": visit.get("estimatedDepartureTime"),
                                    "scheduledMinutesUntilDeparture": visit.get("scheduledMinutesUntilDeparture"),
                                    "estimatedMinutesUntilDeparture": visit.get("estimatedMinutesUntilDeparture"),
                                    "cancelled": visit.get("departureCancelled", False),
                                    "tripId": visit.get("tripId"),
                                    "platformCode": visit.get("platformCode"),
                                    "stopName": visit.get("stopName"),
                                }
                                departures.append(departure)
                    
                    # Sort by scheduled departure time
                    departures.sort(key=lambda x: x.get("scheduledDepartureTime") or 0)
                    
                    return departures

        except asyncio.TimeoutError as err:
            raise TasTransitApiTimeoutError("Timeout while getting departures") from err
        except aiohttp.ClientError as err:
            raise TasTransitApiConnectionError(f"Connection error: {err}") from err
        except Exception as err:
            raise TasTransitApiError(f"Unexpected error: {err}") from err

    def parse_departure_time(self, time_value: str | int | None) -> datetime | None:
        """Parse departure time (Unix timestamp or string) to datetime object."""
        if time_value is None:
            return None
        
        try:
            # Handle Unix timestamp (milliseconds)
            if isinstance(time_value, int):
                return datetime.fromtimestamp(time_value / 1000.0)
            
            # Handle string timestamps
            if isinstance(time_value, str):
                # Try to parse as integer first (Unix timestamp as string)
                try:
                    timestamp = int(time_value)
                    return datetime.fromtimestamp(timestamp / 1000.0)
                except ValueError:
                    pass
                
                # Try different time formats for ISO strings
                formats = [
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%dT%H:%M:%S.%fZ",
                    "%H:%M:%S",
                    "%H:%M",
                ]
                
                for fmt in formats:
                    try:
                        if "T" in time_value:
                            return datetime.fromisoformat(time_value.replace("Z", "+00:00"))
                        else:
                            # For time-only strings, use today's date
                            time_obj = datetime.strptime(time_value, fmt).time()
                            return datetime.combine(datetime.now().date(), time_obj)
                    except ValueError:
                        continue
            
            _LOGGER.warning("Could not parse time value: %s", time_value)
            return None
            
        except Exception as err:
            _LOGGER.warning("Error parsing time value '%s': %s", time_value, err)
            return None