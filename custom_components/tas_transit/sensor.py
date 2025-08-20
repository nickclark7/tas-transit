"""Sensor platform for Tasmanian Transport integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_STOP_ID,
    CONF_STOP_NAME,
    CONF_STOPS,
    DOMAIN,
    SENSOR_BUS_ROUTE,
    SENSOR_NEXT_BUS,
    SENSOR_TIME_TO_DEPARTURE,
)
from .coordinator import TasTransitDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Tasmanian Transport sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    
    sensors = []
    
    # Create sensors for each configured stop
    for stop_config in config_entry.data[CONF_STOPS]:
        stop_id = stop_config[CONF_STOP_ID]
        stop_name = stop_config[CONF_STOP_NAME]
        
        sensors.extend([
            TasTransitNextBusSensor(coordinator, config_entry, stop_id, stop_name),
            TasTransitTimeToDepartureSensor(coordinator, config_entry, stop_id, stop_name),
            TasTransitBusRouteSensor(coordinator, config_entry, stop_id, stop_name),
        ])
    
    async_add_entities(sensors)


class TasTransitSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Tasmanian Transport sensors."""

    def __init__(
        self,
        coordinator: TasTransitDataUpdateCoordinator,
        config_entry: ConfigEntry,
        stop_id: str,
        stop_name: str,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.stop_id = stop_id
        self.stop_name = stop_name
        self.sensor_type = sensor_type
        self._attr_unique_id = f"{config_entry.entry_id}_{stop_id}_{sensor_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{config_entry.entry_id}_{stop_id}")},
            "name": f"Tasmanian Transport - {stop_name}",
            "manufacturer": "Tasmanian Government",
            "model": "Real-time Transport",
        }
    
    @property
    def stop_data(self) -> dict[str, Any] | None:
        """Get the data for this stop."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get(self.stop_id)


class TasTransitNextBusSensor(TasTransitSensorBase):
    """Sensor for the next bus departure."""

    def __init__(
        self,
        coordinator: TasTransitDataUpdateCoordinator,
        config_entry: ConfigEntry,
        stop_id: str,
        stop_name: str,
    ) -> None:
        """Initialize the next bus sensor."""
        super().__init__(coordinator, config_entry, stop_id, stop_name, SENSOR_NEXT_BUS)
        self._attr_name = f"{stop_name} Next Bus"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:bus"

    @property
    def native_value(self) -> datetime | None:
        """Return the next bus departure time."""
        stop_data = self.stop_data
        if not stop_data or not stop_data.get("next_departure"):
            return None
        
        next_departure = stop_data["next_departure"]
        return self.coordinator._get_scheduled_time(next_departure)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        stop_data = self.stop_data
        if not stop_data or not stop_data.get("next_departure"):
            return {"stop_id": self.stop_id}
        
        next_departure = stop_data["next_departure"]
        scheduled_time = self.coordinator._get_scheduled_time(next_departure)
        estimated_time = self.coordinator._get_estimated_time(next_departure)
        
        attributes = {
            "line_number": next_departure.get("lineNumber", "Unknown"),
            "destination": next_departure.get("destinationName", "Unknown"),
            "trip_id": next_departure.get("tripId", "Unknown"),
            "platform_code": next_departure.get("platformCode", "Unknown"),
            "scheduled_time": scheduled_time,
            "cancelled": next_departure.get("cancelled", False),
            "scheduled_minutes_until": next_departure.get("scheduledMinutesUntilDeparture"),
            "estimated_minutes_until": next_departure.get("estimatedMinutesUntilDeparture"),
            "stop_id": self.stop_id,
            "all_departures": self._get_all_departures_info(),
        }
        
        if estimated_time:
            attributes["estimated_time"] = estimated_time
            
        return attributes

    def _get_all_departures_info(self) -> list[dict[str, Any]]:
        """Get information for all upcoming departures."""
        stop_data = self.stop_data
        if not stop_data:
            return []
        
        departures_info = []
        for departure in stop_data.get("departures", []):
            scheduled_time = self.coordinator._get_scheduled_time(departure)
            estimated_time = self.coordinator._get_estimated_time(departure)
            
            info = {
                "line_number": departure.get("lineNumber", "Unknown"),
                "destination": departure.get("destinationName", "Unknown"),
                "scheduled_time": scheduled_time.isoformat() if scheduled_time else None,
                "estimated_time": estimated_time.isoformat() if estimated_time else None,
                "scheduled_minutes_until": departure.get("scheduledMinutesUntilDeparture"),
                "estimated_minutes_until": departure.get("estimatedMinutesUntilDeparture"),
                "cancelled": departure.get("cancelled", False),
                "trip_id": departure.get("tripId"),
                "platform_code": departure.get("platformCode"),
            }
            departures_info.append(info)
        
        return departures_info




class TasTransitTimeToDepartureSensor(TasTransitSensorBase):
    """Sensor for time until bus departure."""

    def __init__(
        self,
        coordinator: TasTransitDataUpdateCoordinator,
        config_entry: ConfigEntry,
        stop_id: str,
        stop_name: str,
    ) -> None:
        """Initialize the time to departure sensor."""
        super().__init__(coordinator, config_entry, stop_id, stop_name, SENSOR_TIME_TO_DEPARTURE)
        self._attr_name = f"{stop_name} Time to Departure"
        self._attr_native_unit_of_measurement = "min"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> int | None:
        """Return the time until departure in minutes."""
        stop_data = self.stop_data
        if not stop_data:
            return None
        
        return stop_data.get("time_to_departure")
    
    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "stop_id": self.stop_id,
        }



class TasTransitBusRouteSensor(TasTransitSensorBase):
    """Sensor for bus route information."""

    def __init__(
        self,
        coordinator: TasTransitDataUpdateCoordinator,
        config_entry: ConfigEntry,
        stop_id: str,
        stop_name: str,
    ) -> None:
        """Initialize the bus route sensor."""
        super().__init__(coordinator, config_entry, stop_id, stop_name, SENSOR_BUS_ROUTE)
        self._attr_name = f"{stop_name} Bus Route"
        self._attr_icon = "mdi:routes"

    @property
    def native_value(self) -> str | None:
        """Return the bus route."""
        stop_data = self.stop_data
        if not stop_data or not stop_data.get("next_departure"):
            return None
        
        next_departure = stop_data["next_departure"]
        return next_departure.get("lineNumber", "Unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        stop_data = self.stop_data
        if not stop_data or not stop_data.get("next_departure"):
            return {"stop_id": self.stop_id}
        
        next_departure = stop_data["next_departure"]
        return {
            "destination": next_departure.get("destinationName", "Unknown"),
            "trip_id": next_departure.get("tripId", "Unknown"),
            "platform_code": next_departure.get("platformCode", "Unknown"),
            "cancelled": next_departure.get("cancelled", False),
            "scheduled_minutes_until": next_departure.get("scheduledMinutesUntilDeparture"),
            "estimated_minutes_until": next_departure.get("estimatedMinutesUntilDeparture"),
            "stop_id": self.stop_id,
            "all_departures": self._get_all_departures_info(),
        }

    def _get_all_departures_info(self) -> list[dict[str, Any]]:
        """Get information for all upcoming departures."""
        stop_data = self.stop_data
        if not stop_data:
            return []
        
        departures_info = []
        for departure in stop_data.get("departures", []):
            scheduled_time = self.coordinator._get_scheduled_time(departure)
            estimated_time = self.coordinator._get_estimated_time(departure)
            
            info = {
                "line_number": departure.get("lineNumber", "Unknown"),
                "destination": departure.get("destinationName", "Unknown"),
                "scheduled_time": scheduled_time.isoformat() if scheduled_time else None,
                "estimated_time": estimated_time.isoformat() if estimated_time else None,
                "scheduled_minutes_until": departure.get("scheduledMinutesUntilDeparture"),
                "estimated_minutes_until": departure.get("estimatedMinutesUntilDeparture"),
                "cancelled": departure.get("cancelled", False),
                "trip_id": departure.get("tripId"),
                "platform_code": departure.get("platformCode"),
            }
            departures_info.append(info)
        
        return departures_info