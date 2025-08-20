"""Test the Tasmanian Transport coordinator."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.tas_transit.const import (
    CONF_STOP_ID,
    CONF_STOP_NAME,
    CONF_STOPS,
    UPDATE_INTERVAL_DEFAULT,
    UPDATE_INTERVAL_FREQUENT,
    UPDATE_INTERVAL_THRESHOLD,
)
from custom_components.tas_transit.coordinator import TasTransitDataUpdateCoordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    return ConfigEntry(
        domain="tas_transit",
        title="Test Stop",
        data={
            CONF_STOPS: [
                {
                    CONF_STOP_ID: "7109023",
                    CONF_STOP_NAME: "Test Stop",
                }
            ]
        },
        entry_id="test_entry",
    )


@pytest.fixture
def coordinator(hass: HomeAssistant, mock_config_entry):
    """Create a coordinator for testing."""
    return TasTransitDataUpdateCoordinator(
        hass=hass,
        logger=None,
        name="test",
        update_interval=timedelta(seconds=UPDATE_INTERVAL_DEFAULT),
        config_entry=mock_config_entry,
    )


async def test_schedule_frequent_updates_when_bus_soon(coordinator):
    """Test that coordinator schedules frequent updates when bus is within threshold."""
    # Mock that a bus is departing in 30 minutes (within threshold)
    await coordinator._schedule_next_update(30)
    
    assert coordinator._current_interval == UPDATE_INTERVAL_FREQUENT
    assert coordinator.update_interval.total_seconds() == UPDATE_INTERVAL_FREQUENT


async def test_schedule_default_updates_when_no_bus_soon(coordinator):
    """Test that coordinator uses default interval when no bus within threshold."""
    # Mock that next bus is in 90 minutes (beyond threshold)
    await coordinator._schedule_next_update(90)
    
    assert coordinator._current_interval == UPDATE_INTERVAL_DEFAULT
    assert coordinator.update_interval.total_seconds() == UPDATE_INTERVAL_DEFAULT


async def test_schedule_default_updates_when_no_departures(coordinator):
    """Test that coordinator uses default interval when no departures."""
    await coordinator._schedule_next_update(None)
    
    assert coordinator._current_interval == UPDATE_INTERVAL_DEFAULT
    assert coordinator.update_interval.total_seconds() == UPDATE_INTERVAL_DEFAULT


async def test_interval_switching(coordinator):
    """Test that interval switches correctly between frequent and default."""
    # Start with frequent updates
    await coordinator._schedule_next_update(30)
    assert coordinator._current_interval == UPDATE_INTERVAL_FREQUENT
    
    # Switch to default when bus is far away
    await coordinator._schedule_next_update(90)
    assert coordinator._current_interval == UPDATE_INTERVAL_DEFAULT
    
    # Switch back to frequent when bus approaches
    await coordinator._schedule_next_update(45)
    assert coordinator._current_interval == UPDATE_INTERVAL_FREQUENT


async def test_update_data_tracks_minimum_departure_time(coordinator):
    """Test that update data tracks the minimum departure time across all stops."""
    mock_departures = [
        {
            "scheduledArrivalTime": (datetime.now() + timedelta(minutes=30)).isoformat(),
            "route": "Route 1",
            "destination": "Test Destination"
        }
    ]
    
    with patch.object(coordinator.api, 'get_stop_departures', return_value=mock_departures):
        with patch.object(coordinator, '_schedule_next_update') as mock_schedule:
            data = await coordinator._async_update_data()
            
            # Verify that schedule_next_update was called with a time around 30 minutes
            mock_schedule.assert_called_once()
            called_time = mock_schedule.call_args[0][0]
            assert called_time is not None
            assert 25 <= called_time <= 35  # Allow some variance for test execution time


async def test_shutdown_cancels_pending_updates(coordinator):
    """Test that shutdown cancels any pending update calls."""
    # Schedule an update
    await coordinator._schedule_next_update(30)
    
    # Verify we have a pending call
    assert coordinator._next_update_call is not None
    
    # Shutdown should cancel it
    await coordinator.async_shutdown()
    assert coordinator._next_update_call is None


@pytest.mark.parametrize("departure_time,expected_interval", [
    (15, UPDATE_INTERVAL_FREQUENT),  # Within threshold
    (45, UPDATE_INTERVAL_FREQUENT),  # Within threshold
    (60, UPDATE_INTERVAL_FREQUENT),  # At threshold
    (61, UPDATE_INTERVAL_DEFAULT),   # Beyond threshold
    (120, UPDATE_INTERVAL_DEFAULT),  # Well beyond threshold
    (None, UPDATE_INTERVAL_DEFAULT), # No departures
])
async def test_update_interval_selection(coordinator, departure_time, expected_interval):
    """Test update interval selection for various departure times."""
    await coordinator._schedule_next_update(departure_time)
    assert coordinator._current_interval == expected_interval