"""Test the Tasmanian Transport API client."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from custom_components.tas_transit.api import (
    TasTransitApi,
    TasTransitApiConnectionError,
    TasTransitApiError,
    TasTransitApiTimeoutError,
)


@pytest.fixture
def api_client():
    """Create an API client for testing."""
    return TasTransitApi()


@pytest.fixture
def mock_response():
    """Mock aiohttp response."""
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=[
        {
            "id": "7109023",
            "name": "Grove Shop",
            "location": {"latitude": -42.88369, "longitude": 147.33251}
        }
    ])
    return mock_resp


async def test_search_stops_by_location_success(api_client, mock_response):
    """Test successful stop search."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await api_client.search_stops_by_location(
            latitude=-42.88369,
            longitude=147.33251,
            query="Grove"
        )
        
        assert len(result) == 1
        assert result[0]["id"] == "7109023"
        assert result[0]["name"] == "Grove Shop"


async def test_search_stops_by_location_timeout(api_client):
    """Test timeout error handling."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.side_effect = asyncio.TimeoutError()
        
        with pytest.raises(TasTransitApiTimeoutError):
            await api_client.search_stops_by_location(
                latitude=-42.88369,
                longitude=147.33251
            )


async def test_search_stops_by_location_connection_error(api_client):
    """Test connection error handling."""
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.side_effect = aiohttp.ClientError("Connection failed")
        
        with pytest.raises(TasTransitApiConnectionError):
            await api_client.search_stops_by_location(
                latitude=-42.88369,
                longitude=147.33251
            )


async def test_get_stop_departures_success(api_client):
    """Test successful departure retrieval."""
    mock_departures = [
        {
            "scheduledArrivalTime": "2024-01-01T08:13:00",
            "estimatedDepartureTime": "2024-01-01T08:15:00",
            "route": "Route 1",
            "destination": "Hobart"
        }
    ]
    
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_departures)
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await api_client.get_stop_departures("7109023")
        
        assert len(result) == 1
        assert result[0]["route"] == "Route 1"
        assert result[0]["destination"] == "Hobart"


async def test_parse_departure_time_iso_format(api_client):
    """Test parsing ISO format datetime."""
    time_str = "2024-01-01T08:13:00"
    result = api_client.parse_departure_time(time_str)
    
    assert result is not None
    assert result.hour == 8
    assert result.minute == 13


async def test_parse_departure_time_time_only(api_client):
    """Test parsing time-only format."""
    time_str = "08:13"
    result = api_client.parse_departure_time(time_str)
    
    assert result is not None
    assert result.hour == 8
    assert result.minute == 13


async def test_parse_departure_time_invalid(api_client):
    """Test parsing invalid time format."""
    time_str = "invalid"
    result = api_client.parse_departure_time(time_str)
    
    assert result is None


async def test_close_session(api_client):
    """Test closing the session."""
    # Create a session
    await api_client._get_session()
    
    # Close it
    await api_client.close()
    
    # Verify it's closed
    assert api_client._session is None or api_client._session.closed