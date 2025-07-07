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
    CONF_DEPARTURE_STOP_NAME,
    CONF_EARLY_THRESHOLD,
    CONF_LATE_THRESHOLD,
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
        self._last_bus_status = None
        self._last_departure_reminder = None
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

        await self._check_bus_status_notifications()
        await self._check_departure_reminder_notifications()

    async def _check_bus_status_notifications(self) -> None:
        """Check for bus status change notifications."""
        current_status = self.coordinator.data.get("bus_status")
        
        if current_status != self._last_bus_status:
            # Status changed, send notification if needed
            if current_status in [BUS_STATUS_EARLY, BUS_STATUS_LATE]:
                await self._send_bus_status_notification(current_status)
            
            self._last_bus_status = current_status

    async def _check_departure_reminder_notifications(self) -> None:
        """Check for departure reminder notifications."""
        time_to_departure = self.coordinator.data.get("time_to_departure")
        
        if time_to_departure is None:
            return
        
        time_to_get_there = self.config_entry.data[CONF_TIME_TO_GET_THERE]
        departure_reminder = self.config_entry.data[CONF_DEPARTURE_REMINDER]
        
        # Calculate when to send the reminder
        reminder_time = time_to_departure - time_to_get_there
        
        # Send reminder if it's time and we haven't sent it yet
        if (
            reminder_time <= departure_reminder
            and reminder_time > 0
            and self._last_departure_reminder != time_to_departure
        ):
            await self._send_departure_reminder_notification(reminder_time)
            self._last_departure_reminder = time_to_departure

    async def _send_bus_status_notification(self, status: str) -> None:
        """Send a notification about bus status change."""
        stop_name = self.config_entry.data[CONF_DEPARTURE_STOP_NAME]
        
        if status == BUS_STATUS_EARLY:
            title = "🚌 Bus Running Early"
            message = f"Your bus from {stop_name} is running early. Check the schedule!"
        elif status == BUS_STATUS_LATE:
            title = "🚌 Bus Running Late"
            message = f"Your bus from {stop_name} is running late. Plan accordingly!"
        else:
            return
        
        await self._send_notification(title, message, "bus_status")

    async def _send_departure_reminder_notification(self, minutes_to_leave: int) -> None:
        """Send a notification reminder to leave for the bus."""
        stop_name = self.config_entry.data[CONF_DEPARTURE_STOP_NAME]
        
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