"""Constants for the Tasmanian Transport integration."""
from typing import Final

DOMAIN: Final = "tas_transit"

# API Configuration
API_BASE_URL: Final = "https://real-time.transport.tas.gov.au/timetable/rest"
API_STOPS_SEARCH: Final = f"{API_BASE_URL}/stops/searchbylocation"
API_STOPDISPLAYS: Final = f"{API_BASE_URL}/stopdisplays"
API_TIMEOUT: Final = 30

# Update Intervals
UPDATE_INTERVAL_DEFAULT: Final = 60   # 1 minute - default update interval
UPDATE_INTERVAL_FREQUENT: Final = 20  # 20 seconds - when bus within 30 minutes
UPDATE_INTERVAL_THRESHOLD: Final = 30 # 30 minutes - switch to frequent updates

# Configuration Keys
CONF_STOPS: Final = "stops"
CONF_STOP_ID: Final = "stop_id"
CONF_STOP_NAME: Final = "stop_name"

# Sensor Names
SENSOR_NEXT_BUS: Final = "next_bus_departure"
SENSOR_TIME_TO_DEPARTURE: Final = "time_to_departure"
SENSOR_BUS_ROUTE: Final = "bus_route"

# Web URLs
TRANSPORT_WEB_URL: Final = "https://real-time.transport.tas.gov.au/timetable/#?stop="