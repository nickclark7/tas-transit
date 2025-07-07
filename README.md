# Tasmanian Transport Home Assistant Integration

A custom Home Assistant integration for tracking real-time bus departures using the Tasmanian Government's transport API.

## Features

- **Real-time Bus Tracking**: Get live departure times for your bus stop
- **Smart Notifications**: Receive alerts when buses are running early or late
- **Departure Reminders**: Get notified when it's time to leave for your bus
- **Multiple Sensors**: Track various aspects of your bus journey
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

## Configuration

1. Go to Settings > Devices & Services > Add Integration
2. Search for "Tasmanian Transport"
3. Configure the following settings:
   - **Departure Stop Name**: The name of your bus stop (e.g., "Grove Shop")
   - **Arrival Destination**: Where you're going (e.g., "Hobart")
   - **Scheduled Departure Time**: Your usual bus time (e.g., "8:13")
   - **Time to Get There**: How long it takes to walk to the stop (minutes)
   - **Early/Late Thresholds**: When to consider a bus early or late (minutes)
   - **Departure Reminder**: How many minutes before departure to remind you

## Sensors

The integration creates the following sensors:

- **Next Bus Departure**: Shows the next bus departure time
- **Bus Status**: Indicates if the bus is on time, early, or late
- **Time to Departure**: Minutes until the bus departs
- **Time to Leave**: Minutes until you should leave for the bus stop
- **Bus Route**: Route information and destination

## Notifications

The integration can send notifications for:

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
          message: "It's time to leave for your bus!"
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
          message: "Your bus is running late. Plan accordingly!"
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