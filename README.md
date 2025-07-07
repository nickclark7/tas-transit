# Tasmanian Transport Home Assistant Integration

A custom Home Assistant integration for tracking real-time bus departures using the Tasmanian Government's transport API.

## Features

- **Real-time Bus Tracking**: Get live departure times for your bus stops
- **Multiple Stop Support**: Track multiple bus stops (e.g., work and home routes)
- **Smart Notifications**: Receive alerts when buses are running early or late
- **Departure Reminders**: Get notified when it's time to leave for your bus
- **Multiple Sensors**: Track various aspects of your bus journey for each stop
- **Easy Configuration**: Simple setup through Home Assistant's UI

## Installation

### HACS (Recommended)

1. Install HACS if you haven't already
2. Add this repository as a custom repository in HACS
3. Search for "Tasmanian Transport" in HACS
4. Download and install the integration
5. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/tas_transit` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Go to Settings > Devices & Services > Add Integration
4. Search for "Tasmanian Transport"

## Finding Your Stop ID

To configure this integration, you need your bus stop ID:

1. Visit the [Tasmanian Transport website](https://real-time.transport.tas.gov.au/timetable/#?stop=7109023)
2. Search for your bus stop
3. Once you find your stop, copy the ID from the URL (e.g., `7109023` from `.../#?stop=7109023`)

## Configuration

1. Go to Settings > Devices & Services > Add Integration
2. Search for "Tasmanian Transport"
3. Configure the following settings:
   - **Stop ID**: Your bus stop ID (e.g., "7109023")
   - **Scheduled Departure Time**: Your usual bus time in 24-hour format (e.g., "08:13")
   - **Time to Get There**: How long it takes to walk to the stop (minutes)
   - **Early Threshold**: How many minutes early is considered "early" for notifications
   - **Late Threshold**: How many minutes late is considered "late" for notifications
   - **Departure Reminder**: How many minutes before departure to remind you to leave

### Adding Multiple Stops

To track multiple bus stops (e.g., one for going to work, another for coming home):

1. Set up your first stop as described above
2. Go to Settings > Devices & Services
3. Find your "Tasmanian Transport" integration
4. Click "Configure" and add another stop with a different Stop ID

## Sensors

The integration creates the following sensors for each configured stop:

- **[Stop Name] Next Bus Departure**: Shows the next bus departure time
- **[Stop Name] Bus Status**: Indicates if the bus is on time, early, or late
- **[Stop Name] Time to Departure**: Minutes until the bus departs
- **[Stop Name] Time to Leave**: Minutes until you should leave for the bus stop
- **[Stop Name] Bus Route**: Route information and destination

For example, if you configure a stop named "Grove Shop", you'll get:
- `sensor.grove_shop_next_bus_departure`
- `sensor.grove_shop_bus_status`
- `sensor.grove_shop_time_to_departure`
- `sensor.grove_shop_time_to_leave`
- `sensor.grove_shop_bus_route`

## Notifications

The integration can send notifications for each stop:

- **Bus Status Changes**: When your bus is running early or late
- **Departure Reminders**: When it's time to leave for the bus stop

Make sure you have the Home Assistant mobile app or another notification service configured to receive these alerts.

## Example Automations

### Departure Reminder

```yaml
automation:
  - alias: "Bus Departure Reminder"
    trigger:
      - platform: numeric_state
        entity_id: sensor.grove_shop_time_to_leave
        below: 1
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🏃 Time to Leave!"
          message: "It's time to leave for your bus at Grove Shop!"
```

### Bus Status Alert

```yaml
automation:
  - alias: "Bus Status Alert"
    trigger:
      - platform: state
        entity_id: sensor.grove_shop_bus_status
        to: "late"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🚌 Bus Running Late"
          message: "Your bus from Grove Shop is running late. Plan accordingly!"
```

### Multiple Stop Automation

```yaml
automation:
  - alias: "Any Bus Running Late"
    trigger:
      - platform: state
        entity_id: 
          - sensor.grove_shop_bus_status
          - sensor.work_stop_bus_status
        to: "late"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🚌 Bus Alert"
          message: "Bus from {{ trigger.entity_id | replace('sensor.', '') | replace('_bus_status', '') | replace('_', ' ') | title }} is running late!"
```

## API Information

This integration uses the Tasmanian Government's real-time transport API:
- Base URL: `https://real-time.transport.tas.gov.au/timetable/rest`
- Stop Search: `/stops/searchbylocation`
- Departures: `/stops/{stop_id}/departures`

## Support

For issues and feature requests, please visit the [GitHub repository](https://github.com/user/tas-transit).

## License

This project is licensed under the MIT License - see the LICENSE file for details.