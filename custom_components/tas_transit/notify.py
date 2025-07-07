"""Notification services for Tasmanian Transport integration."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    BUS_STATUS_EARLY,
    BUS_STATUS_LATE,
    CONF_DEPARTURE_REMINDER,
    CONF_EARLY_THRESHOLD,
    CONF_LATE_THRESHOLD,
    CONF_STOP_ID,
    CONF_STOP_NAME,
    CONF_STOPS,
    CONF_TIME_TO_GET_THERE,
    DOMAIN,
)
from .coordinator import TasTransitDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class TasTransitNotificationService:
    """Service for sending notifications about bus status."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: TasTransitDataUpdateCoordinator,
        config_entry,
    ) -> None:
        """Initialize the notification service."""
        self.hass = hass
        self.coordinator = coordinator
        self.config_entry = config_entry
        self._last_bus_status = {}  # Track status per stop
        self._last_departure_reminder = {}  # Track reminders per stop
        self._unsub_timer = None

    async def async_setup(self) -> None:
        """Set up the notification service."""
        # Schedule periodic checks for notifications
        self._unsub_timer = async_track_time_interval(
            self.hass,
            self._check_notifications,
            timedelta(minutes=1),
        )

    async def async_shutdown(self) -> None:
        """Shutdown the notification service."""
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None

    @callback
    async def _check_notifications(self, now: datetime) -> None:
        """Check if we need to send any notifications."""
        if not self.coordinator.data:
            return

        # Check notifications for each stop
        for stop_config in self.config_entry.data[CONF_STOPS]:
            stop_id = stop_config[CONF_STOP_ID]
            stop_data = self.coordinator.data.get(stop_id)
            
            if stop_data:
                await self._check_bus_status_notifications(stop_id, stop_config, stop_data)
                await self._check_departure_reminder_notifications(stop_id, stop_config, stop_data)

    async def _check_bus_status_notifications(self, stop_id: str, stop_config: dict, stop_data: dict) -> None:
        """Check for bus status change notifications."""
        current_status = stop_data.get("bus_status")
        last_status = self._last_bus_status.get(stop_id)
        
        if current_status != last_status:
            # Status changed, send notification if needed
            if current_status in [BUS_STATUS_EARLY, BUS_STATUS_LATE]:
                await self._send_bus_status_notification(stop_config, current_status)
            
            self._last_bus_status[stop_id] = current_status

    async def _check_departure_reminder_notifications(self, stop_id: str, stop_config: dict, stop_data: dict) -> None:
        """Check for departure reminder notifications."""
        time_to_departure = stop_data.get("time_to_departure")
        
        if time_to_departure is None:
            return
        
        time_to_get_there = stop_config[CONF_TIME_TO_GET_THERE]
        departure_reminder = stop_config[CONF_DEPARTURE_REMINDER]
        
        # Calculate when to send the reminder
        reminder_time = time_to_departure - time_to_get_there
        
        # Send reminder if it's time and we haven't sent it yet
        last_reminder = self._last_departure_reminder.get(stop_id)
        if (
            reminder_time <= departure_reminder
            and reminder_time > 0
            and last_reminder != time_to_departure
        ):
            await self._send_departure_reminder_notification(stop_config, reminder_time)
            self._last_departure_reminder[stop_id] = time_to_departure

    async def _send_bus_status_notification(self, stop_config: dict, status: str) -> None:
        """Send a notification about bus status change."""
        stop_name = stop_config[CONF_STOP_NAME]
        
        if status == BUS_STATUS_EARLY:
            title = "🚌 Bus Running Early"
            message = f"Your bus from {stop_name} is running early. Check the schedule!"
        elif status == BUS_STATUS_LATE:
            title = "🚌 Bus Running Late"
            message = f"Your bus from {stop_name} is running late. Plan accordingly!"
        else:
            return
        
        await self._send_notification(title, message, "bus_status")

    async def _send_departure_reminder_notification(self, stop_config: dict, minutes_to_leave: int) -> None:
        """Send a notification reminder to leave for the bus."""
        stop_name = stop_config[CONF_STOP_NAME]
        
        if minutes_to_leave <= 0:
            title = "🏃 Time to Leave!"
            message = f"It's time to leave for your bus at {stop_name}!"
        else:
            title = "⏰ Bus Departure Reminder"
            message = f"Leave in {minutes_to_leave} minutes for your bus at {stop_name}!"
        
        await self._send_notification(title, message, "departure_reminder")

    async def _send_notification(
        self,
        title: str,
        message: str,
        notification_type: str,
    ) -> None:
        """Send a notification using Home Assistant's notification service."""
        try:
            await self.hass.services.async_call(
                "notify",
                "notify",
                {
                    "title": title,
                    "message": message,
                    "data": {
                        "tag": f"{DOMAIN}_{notification_type}",
                        "group": DOMAIN,
                        "channel": "Bus Notifications",
                        "importance": "high",
                        "notification_icon": "mdi:bus",
                    },
                },
            )
            _LOGGER.debug("Sent notification: %s - %s", title, message)
        except Exception as err:
            _LOGGER.error("Failed to send notification: %s", err)