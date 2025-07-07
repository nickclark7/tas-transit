"""Test the Tasmanian Transport config flow."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.tas_transit.const import DOMAIN


@pytest.fixture
def mock_setup_entry():
    """Mock setting up a config entry."""
    with patch(
        "custom_components.tas_transit.async_setup_entry",
        return_value=True,
    ):
        yield


@pytest.fixture
def mock_api():
    """Mock the API client."""
    with patch("custom_components.tas_transit.config_flow.TasTransitApi") as mock_api:
        api_instance = mock_api.return_value
        api_instance.search_stops_by_location = AsyncMock(return_value=[
            {
                "id": "7109023",
                "name": "Grove Shop",
                "location": {"latitude": -42.88369, "longitude": 147.33251}
            }
        ])
        yield api_instance


async def test_form(hass: HomeAssistant, mock_setup_entry, mock_api) -> None:
    """Test we get the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "departure_stop_name": "Grove Shop",
            "arrival_destination": "Hobart",
            "scheduled_departure_time": "8:13",
            "time_to_get_there": 5,
            "early_threshold": 2,
            "late_threshold": 5,
            "departure_reminder": 10,
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["title"] == "Bus from Grove Shop"
    assert result2["data"] == {
        "departure_stop_id": "7109023",
        "departure_stop_name": "Grove Shop",
        "arrival_destination": "Hobart",
        "scheduled_departure_time": "8:13",
        "time_to_get_there": 5,
        "early_threshold": 2,
        "late_threshold": 5,
        "departure_reminder": 10,
    }


async def test_form_invalid_time(hass: HomeAssistant, mock_api) -> None:
    """Test we handle invalid time format."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "departure_stop_name": "Grove Shop",
            "arrival_destination": "Hobart",
            "scheduled_departure_time": "invalid",
            "time_to_get_there": 5,
            "early_threshold": 2,
            "late_threshold": 5,
            "departure_reminder": 10,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"scheduled_departure_time": "invalid_time_format"}


async def test_form_stop_not_found(hass: HomeAssistant, mock_api) -> None:
    """Test we handle stop not found."""
    mock_api.search_stops_by_location.return_value = []

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "departure_stop_name": "Nonexistent Stop",
            "arrival_destination": "Hobart",
            "scheduled_departure_time": "8:13",
            "time_to_get_there": 5,
            "early_threshold": 2,
            "late_threshold": 5,
            "departure_reminder": 10,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "stop_not_found"}


async def test_form_api_error(hass: HomeAssistant, mock_api) -> None:
    """Test we handle API errors."""
    mock_api.search_stops_by_location.side_effect = Exception("API Error")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "departure_stop_name": "Grove Shop",
            "arrival_destination": "Hobart",
            "scheduled_departure_time": "8:13",
            "time_to_get_there": 5,
            "early_threshold": 2,
            "late_threshold": 5,
            "departure_reminder": 10,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unknown"}