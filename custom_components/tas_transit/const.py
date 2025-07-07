"""Constants for the Tasmanian Transport integration."""
from typing import Final

DOMAIN: Final = "tas_transit"

# API Configuration
API_BASE_URL: Final = "https://real-time.transport.tas.gov.au/timetable/rest"
API_STOPS_SEARCH: Final = f"{API_BASE_URL}/stops/searchbylocation"
API_TIMEOUT: Final = 30
UPDATE_INTERVAL: Final = 60  # seconds

# Configuration Keys
CONF_DEPARTURE_STOP_ID: Final = "departure_stop_id"
CONF_DEPARTURE_STOP_NAME: Final = "departure_stop_name"
CONF_ARRIVAL_DESTINATION: Final = "arrival_destination"
CONF_SCHEDULED_DEPARTURE_TIME: Final = "scheduled_departure_time"
CONF_TIME_TO_GET_THERE: Final = "time_to_get_there"
CONF_EARLY_THRESHOLD: Final = "early_threshold"
CONF_LATE_THRESHOLD: Final = "late_threshold"
CONF_DEPARTURE_REMINDER: Final = "departure_reminder"

# Default Values
DEFAULT_TIME_TO_GET_THERE: Final = 5  # minutes
DEFAULT_EARLY_THRESHOLD: Final = 2  # minutes
DEFAULT_LATE_THRESHOLD: Final = 5  # minutes
DEFAULT_DEPARTURE_REMINDER: Final = 10  # minutes before departure

# Sensor Names
SENSOR_NEXT_BUS: Final = "next_bus_departure"
SENSOR_BUS_STATUS: Final = "bus_status"
SENSOR_TIME_TO_DEPARTURE: Final = "time_to_departure"
SENSOR_TIME_TO_LEAVE: Final = "time_to_leave"
SENSOR_BUS_ROUTE: Final = "bus_route"

# Bus Status
BUS_STATUS_ON_TIME: Final = "on_time"
BUS_STATUS_EARLY: Final = "early"
BUS_STATUS_LATE: Final = "late"
BUS_STATUS_CANCELLED: Final = "cancelled"
BUS_STATUS_UNKNOWN: Final = "unknown"