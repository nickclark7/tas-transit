"""Test the Tasmanian Transport coordinator."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.tas_transit.const import (
    CONF_DESTINATION_FILTERS,
    CONF_FILTER_MODE,
    CONF_LINE_FILTERS,
    CONF_STOP_ID,
    CONF_STOP_NAME,
    CONF_STOPS,
    FILTER_MODE_EXCLUDE,
    FILTER_MODE_INCLUDE,
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


# Filter functionality tests

@pytest.fixture
def mock_departures():
    """Create mock departure data for filter testing."""
    return [
        {
            "lineNumber": "X58",
            "destinationName": "Mount Nelson",
            "scheduledMinutesUntilDeparture": 10,
            "estimatedMinutesUntilDeparture": 12,
            "cancelled": False,
        },
        {
            "lineNumber": "457",
            "destinationName": "Mount Nelson",
            "scheduledMinutesUntilDeparture": 25,
            "estimatedMinutesUntilDeparture": None,
            "cancelled": False,
        },
        {
            "lineNumber": "401",
            "destinationName": "Lower Sandy Bay",
            "scheduledMinutesUntilDeparture": 15,
            "estimatedMinutesUntilDeparture": 15,
            "cancelled": False,
        },
        {
            "lineNumber": "501",
            "destinationName": "University",
            "scheduledMinutesUntilDeparture": 5,
            "estimatedMinutesUntilDeparture": 6,
            "cancelled": False,
        },
    ]


def test_apply_filters_no_filters(coordinator, mock_departures):
    """Test that no filters returns all departures."""
    stop_config = {CONF_STOP_ID: "7109023", CONF_STOP_NAME: "Test Stop"}
    result = coordinator._apply_filters(mock_departures, stop_config)
    assert len(result) == len(mock_departures)
    assert result == mock_departures


def test_apply_filters_line_include(coordinator, mock_departures):
    """Test line number filter in include mode."""
    stop_config = {
        CONF_STOP_ID: "7109023",
        CONF_STOP_NAME: "Test Stop",
        CONF_LINE_FILTERS: ["X58", "457"],
        CONF_FILTER_MODE: FILTER_MODE_INCLUDE,
    }
    result = coordinator._apply_filters(mock_departures, stop_config)
    assert len(result) == 2
    line_numbers = [dep["lineNumber"] for dep in result]
    assert "X58" in line_numbers
    assert "457" in line_numbers


def test_apply_filters_line_exclude(coordinator, mock_departures):
    """Test line number filter in exclude mode."""
    stop_config = {
        CONF_STOP_ID: "7109023",
        CONF_STOP_NAME: "Test Stop",
        CONF_LINE_FILTERS: ["X58"],
        CONF_FILTER_MODE: FILTER_MODE_EXCLUDE,
    }
    result = coordinator._apply_filters(mock_departures, stop_config)
    assert len(result) == 3
    line_numbers = [dep["lineNumber"] for dep in result]
    assert "X58" not in line_numbers
    assert "457" in line_numbers
    assert "401" in line_numbers
    assert "501" in line_numbers


def test_apply_filters_destination_include(coordinator, mock_departures):
    """Test destination filter in include mode."""
    stop_config = {
        CONF_STOP_ID: "7109023",
        CONF_STOP_NAME: "Test Stop",
        CONF_DESTINATION_FILTERS: ["Mount Nelson"],
        CONF_FILTER_MODE: FILTER_MODE_INCLUDE,
    }
    result = coordinator._apply_filters(mock_departures, stop_config)
    assert len(result) == 2
    destinations = [dep["destinationName"] for dep in result]
    assert all("Mount Nelson" in dest for dest in destinations)


def test_apply_filters_destination_exclude(coordinator, mock_departures):
    """Test destination filter in exclude mode."""
    stop_config = {
        CONF_STOP_ID: "7109023",
        CONF_STOP_NAME: "Test Stop",
        CONF_DESTINATION_FILTERS: ["University"],
        CONF_FILTER_MODE: FILTER_MODE_EXCLUDE,
    }
    result = coordinator._apply_filters(mock_departures, stop_config)
    assert len(result) == 3
    destinations = [dep["destinationName"] for dep in result]
    assert all("University" not in dest for dest in destinations)


def test_apply_filters_combined_include(coordinator, mock_departures):
    """Test combined line and destination filters in include mode."""
    stop_config = {
        CONF_STOP_ID: "7109023",
        CONF_STOP_NAME: "Test Stop",
        CONF_LINE_FILTERS: ["X58"],
        CONF_DESTINATION_FILTERS: ["University"],
        CONF_FILTER_MODE: FILTER_MODE_INCLUDE,
    }
    result = coordinator._apply_filters(mock_departures, stop_config)
    # Should include X58 (matches line) OR University destination (matches dest)
    assert len(result) == 2
    result_data = [(dep["lineNumber"], dep["destinationName"]) for dep in result]
    assert ("X58", "Mount Nelson") in result_data
    assert ("501", "University") in result_data


def test_apply_filters_combined_exclude(coordinator, mock_departures):
    """Test combined line and destination filters in exclude mode."""
    stop_config = {
        CONF_STOP_ID: "7109023",
        CONF_STOP_NAME: "Test Stop",
        CONF_LINE_FILTERS: ["X58"],
        CONF_DESTINATION_FILTERS: ["University"],
        CONF_FILTER_MODE: FILTER_MODE_EXCLUDE,
    }
    result = coordinator._apply_filters(mock_departures, stop_config)
    # Should exclude X58 (matches line) OR University destination (matches dest)
    assert len(result) == 2
    result_data = [(dep["lineNumber"], dep["destinationName"]) for dep in result]
    assert ("457", "Mount Nelson") in result_data
    assert ("401", "Lower Sandy Bay") in result_data


def test_matches_line_filter_exact(coordinator):
    """Test exact line number matching."""
    assert coordinator._matches_line_filter("X58", ["X58", "457"]) is True
    assert coordinator._matches_line_filter("401", ["X58", "457"]) is False


def test_matches_line_filter_partial(coordinator):
    """Test partial line number matching."""
    assert coordinator._matches_line_filter("X58", ["58"]) is True
    assert coordinator._matches_line_filter("58", ["X58"]) is True
    assert coordinator._matches_line_filter("401", ["40"]) is True


def test_matches_line_filter_case_insensitive(coordinator):
    """Test case insensitive line number matching."""
    assert coordinator._matches_line_filter("x58", ["X58"]) is True
    assert coordinator._matches_line_filter("X58", ["x58"]) is True


def test_matches_destination_filter_partial(coordinator):
    """Test partial destination matching."""
    assert coordinator._matches_destination_filter("Mount Nelson", ["Mount"]) is True
    assert coordinator._matches_destination_filter("Mount Nelson", ["Nelson"]) is True
    assert coordinator._matches_destination_filter("Lower Sandy Bay", ["Sandy"]) is True
    assert coordinator._matches_destination_filter("University", ["Mount"]) is False


def test_matches_destination_filter_case_insensitive(coordinator):
    """Test case insensitive destination matching."""
    assert coordinator._matches_destination_filter("Mount Nelson", ["mount nelson"]) is True
    assert coordinator._matches_destination_filter("UNIVERSITY", ["university"]) is True
    assert coordinator._matches_destination_filter("lower sandy bay", ["SANDY BAY"]) is True


def test_process_departures_with_filters(coordinator, mock_departures):
    """Test the full _process_departures method with filters."""
    stop_config = {
        CONF_STOP_ID: "7109023",
        CONF_STOP_NAME: "Test Stop",
        CONF_LINE_FILTERS: ["X58", "501"],
        CONF_FILTER_MODE: FILTER_MODE_INCLUDE,
    }
    
    result = coordinator._process_departures(mock_departures, stop_config)
    
    # Should have filtered departures
    assert "departures" in result
    filtered_departures = result["departures"]
    assert len(filtered_departures) == 2
    
    line_numbers = [dep["lineNumber"] for dep in filtered_departures]
    assert "X58" in line_numbers
    assert "501" in line_numbers
    
    # Next departure should be the earliest from filtered results (501 at 5/6 minutes)
    assert result["next_departure"]["lineNumber"] == "501"
    assert result["time_to_departure"] == 6  # Uses estimated time


def test_empty_filter_lists(coordinator, mock_departures):
    """Test behavior with empty filter lists."""
    stop_config = {
        CONF_STOP_ID: "7109023",
        CONF_STOP_NAME: "Test Stop",
        CONF_LINE_FILTERS: [],
        CONF_DESTINATION_FILTERS: [],
        CONF_FILTER_MODE: FILTER_MODE_INCLUDE,
    }
    result = coordinator._apply_filters(mock_departures, stop_config)
    assert len(result) == len(mock_departures)