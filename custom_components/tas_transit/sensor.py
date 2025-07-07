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
    BUS_STATUS_ON_TIME,
    BUS_STATUS_UNKNOWN,
    CONF_DEPARTURE_REMINDER,
    CONF_DEPARTURE_STOP_NAME,
    CONF_SCHEDULED_DEPARTURE_TIME,
    CONF_TIME_TO_GET_THERE,
    DOMAIN,
    SENSOR_BUS_ROUTE,
    SENSOR_BUS_STATUS,
    SENSOR_NEXT_BUS,
    SENSOR_TIME_TO_DEPARTURE,
    SENSOR_TIME_TO_LEAVE,
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
    
    sensors = [
        TasTransitNextBusSensor(coordinator, config_entry),
        TasTransitBusStatusSensor(coordinator, config_entry),
        TasTransitTimeToDepartureSensor(coordinator, config_entry),
        TasTransitTimeToLeaveSensor(coordinator, config_entry),
        TasTransitBusRouteSensor(coordinator, config_entry),
    ]
    
    async_add_entities(sensors)


class TasTransitSensorBase(CoordinatorEntity, SensorEntity):
    """Base class for Tasmanian Transport sensors."""

    def __init__(
        self,
        coordinator: TasTransitDataUpdateCoordinator,
        config_entry: ConfigEntry,
        sensor_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.config_entry = config_entry
        self.sensor_type = sensor_type
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": f"Tasmanian Transport - {config_entry.data[CONF_DEPARTURE_STOP_NAME]}",
            "manufacturer": "Tasmanian Government",
            "model": "Real-time Transport",
        }


class TasTransitNextBusSensor(TasTransitSensorBase):
    """Sensor for the next bus departure."""

    def __init__(
        self,
        coordinator: TasTransitDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the next bus sensor."""
        super().__init__(coordinator, config_entry, SENSOR_NEXT_BUS)
        self._attr_name = f"{config_entry.data[CONF_DEPARTURE_STOP_NAME]} Next Bus"
        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:bus"

    @property
    def native_value(self) -> datetime | None:
        """Return the next bus departure time."""
        if not self.coordinator.data or not self.coordinator.data.get("next_departure"):
            return None
        
        next_departure = self.coordinator.data["next_departure"]
        return self.coordinator._get_scheduled_time(next_departure)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data or not self.coordinator.data.get("next_departure"):
            return {}
        
        next_departure = self.coordinator.data["next_departure"]
        estimated_time = self.coordinator._get_estimated_time(next_departure)
        
        attributes = {
            "route": next_departure.get("route", "Unknown"),
            "destination": next_departure.get("destination", "Unknown"),
            "scheduled_time": self.coordinator._get_scheduled_time(next_departure),
        }
        
        if estimated_time:
            attributes["estimated_time"] = estimated_time
            
        return attributes


class TasTransitBusStatusSensor(TasTransitSensorBase):
    """Sensor for bus status (on time, early, late)."""

    def __init__(
        self,
        coordinator: TasTransitDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the bus status sensor."""
        super().__init__(coordinator, config_entry, SENSOR_BUS_STATUS)
        self._attr_name = f"{config_entry.data[CONF_DEPARTURE_STOP_NAME]} Bus Status"
        self._attr_icon = "mdi:bus-alert"

    @property
    def native_value(self) -> str:
        """Return the bus status."""
        if not self.coordinator.data:
            return BUS_STATUS_UNKNOWN
        
        return self.coordinator.data.get("bus_status", BUS_STATUS_UNKNOWN)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}
        
        return {
            "last_updated": self.coordinator.data.get("last_updated"),
        }


class TasTransitTimeToDepartureSensor(TasTransitSensorBase):
    """Sensor for time until bus departure."""

    def __init__(
        self,
        coordinator: TasTransitDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the time to departure sensor."""
        super().__init__(coordinator, config_entry, SENSOR_TIME_TO_DEPARTURE)
        self._attr_name = f"{config_entry.data[CONF_DEPARTURE_STOP_NAME]} Time to Departure"
        self._attr_native_unit_of_measurement = "min"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:clock-outline"

    @property
    def native_value(self) -> int | None:
        """Return the time until departure in minutes."""
        if not self.coordinator.data:
            return None
        
        return self.coordinator.data.get("time_to_departure")


class TasTransitTimeToLeaveSensor(TasTransitSensorBase):
    """Sensor for when to leave to catch the bus."""

    def __init__(
        self,
        coordinator: TasTransitDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the time to leave sensor."""
        super().__init__(coordinator, config_entry, SENSOR_TIME_TO_LEAVE)
        self._attr_name = f"{config_entry.data[CONF_DEPARTURE_STOP_NAME]} Time to Leave"
        self._attr_native_unit_of_measurement = "min"
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:run"

    @property
    def native_value(self) -> int | None:
        """Return the time until you should leave in minutes."""
        if not self.coordinator.data:
            return None
        
        time_to_departure = self.coordinator.data.get("time_to_departure")
        if time_to_departure is None:
            return None
        
        time_to_get_there = self.config_entry.data[CONF_TIME_TO_GET_THERE]
        time_to_leave = time_to_departure - time_to_get_there
        
        return max(0, time_to_leave)  # Don't return negative values

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        return {
            "time_to_get_there": self.config_entry.data[CONF_TIME_TO_GET_THERE],
            "should_leave_now": self.native_value == 0 if self.native_value is not None else False,
        }


class TasTransitBusRouteSensor(TasTransitSensorBase):
    """Sensor for bus route information."""

    def __init__(
        self,
        coordinator: TasTransitDataUpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the bus route sensor."""
        super().__init__(coordinator, config_entry, SENSOR_BUS_ROUTE)
        self._attr_name = f"{config_entry.data[CONF_DEPARTURE_STOP_NAME]} Bus Route"
        self._attr_icon = "mdi:routes"

    @property
    def native_value(self) -> str | None:
        """Return the bus route."""
        if not self.coordinator.data or not self.coordinator.data.get("next_departure"):
            return None
        
        next_departure = self.coordinator.data["next_departure"]
        return next_departure.get("route", "Unknown")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data or not self.coordinator.data.get("next_departure"):
            return {}
        
        next_departure = self.coordinator.data["next_departure"]
        return {
            "destination": next_departure.get("destination", "Unknown"),
            "operator": next_departure.get("operator", "Unknown"),
        }