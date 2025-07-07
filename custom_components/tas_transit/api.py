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
                    
                    # Extract departures from the stopdisplays response
                    departures = []
                    if isinstance(data, dict) and "departures" in data:
                        departures = data["departures"]
                    
                    return departures

        except asyncio.TimeoutError as err:
            raise TasTransitApiTimeoutError("Timeout while getting departures") from err
        except aiohttp.ClientError as err:
            raise TasTransitApiConnectionError(f"Connection error: {err}") from err
        except Exception as err:
            raise TasTransitApiError(f"Unexpected error: {err}") from err

    def parse_departure_time(self, time_str: str) -> datetime | None:
        """Parse departure time string to datetime object."""
        if not time_str:
            return None
        
        try:
            # Try different time formats that might be used by the API
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
                    if "T" in time_str:
                        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                    else:
                        # For time-only strings, use today's date
                        time_obj = datetime.strptime(time_str, fmt).time()
                        return datetime.combine(datetime.now().date(), time_obj)
                except ValueError:
                    continue
            
            _LOGGER.warning("Could not parse time string: %s", time_str)
            return None
            
        except Exception as err:
            _LOGGER.warning("Error parsing time string '%s': %s", time_str, err)
            return None