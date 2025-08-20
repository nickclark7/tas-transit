# Tasmanian Transport Home Assistant Integration

A third-party Home Assistant integration for tracking real-time bus departures using Tasmania's public transport API.

## Features

- **Real-time Bus Tracking**: Get live departure times for your bus stops
- **Multiple Stop Support**: Track multiple bus stops (e.g., work and home routes) 
- **Comprehensive Data**: Access all upcoming departures with route numbers, destinations, and timing details
- **Unopinionated Sensors**: Raw transit data exposed for flexible user automation and filtering
- **Automatic Updates**: Smart update intervals (1 minute normally, 20 seconds when buses approach)
- **Easy Configuration**: Simple setup through Home Assistant's UI - just enter your stop ID

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

To configure this integration, you need your bus stop ID. Stop IDs consist of your postcode followed by three digits (e.g., 7109023 for postcode 7109):

1. Visit the [Tasmanian Transport website](https://real-time.transport.tas.gov.au/timetable/)
2. Search for your bus stop
3. Once you find your stop, copy the ID from the URL (e.g., `7109023` from `.../#?stop=7109023`)

## Configuration

1. Go to Settings > Devices & Services > Add Integration
2. Search for "Tasmanian Transport"  
3. Enter your **Stop ID** (e.g., "7109023")
4. The integration will automatically fetch and display the stop name for confirmation

That's it! The integration will create sensors that update automatically.

### Adding Multiple Stops

To track multiple bus stops (e.g., one for going to work, another for coming home):

1. Set up your first stop as described above
2. Go to Settings > Devices & Services
3. Find your "Tasmanian Transport" integration
4. Click "Configure" and add another stop with a different Stop ID

## Sensors

The integration creates the following sensors for each configured stop:

- **[Stop Name] Next Bus Departure**: Shows the next bus departure time
- **[Stop Name] Time to Departure**: Minutes until the next bus departs  
- **[Stop Name] Bus Route**: Route number and destination for the next bus

For example, if you configure stop "7109023" (Hobart Interchange), you'll get:
- `sensor.hobart_interchange_next_bus_departure`
- `sensor.hobart_interchange_time_to_departure`  
- `sensor.hobart_interchange_bus_route`

### Sensor Attributes

Each sensor exposes detailed attributes with **all upcoming departures** for flexible filtering:

- **line_number**: Route number (e.g., "401", "X58")
- **destination**: Where the bus is going (e.g., "Lower Sandy Bay", "University")
- **scheduled_time** & **estimated_time**: Departure times (ISO format)
- **scheduled_minutes_until** & **estimated_minutes_until**: Minutes until departure
- **cancelled**: Whether the departure is cancelled
- **trip_id**: Unique trip identifier
- **platform_code**: Platform/stop position (e.g., "D3")
- **all_departures**: Array of all upcoming departures with the above details

## Example Automations

The integration provides raw transit data - you can create your own automations based on your needs.

### Departure Reminder

```yaml
automation:
  - alias: "Bus Departure Reminder"
    trigger:
      - platform: numeric_state
        entity_id: sensor.hobart_interchange_time_to_departure
        below: 10  # Alert when bus is 10 minutes away
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🚌 Bus Approaching"
          message: "Your {{ state_attr('sensor.hobart_interchange_bus_route', 'line_number') }} bus to {{ state_attr('sensor.hobart_interchange_bus_route', 'destination') }} departs in {{ states('sensor.hobart_interchange_time_to_departure') }} minutes!"
```

### Route-Specific Notifications

```yaml
automation:
  - alias: "X58 Bus Alert"
    trigger:
      - platform: state
        entity_id: sensor.hobart_interchange_bus_route
        to: "X58"
    condition:
      - condition: numeric_state
        entity_id: sensor.hobart_interchange_time_to_departure
        below: 15
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "🚌 X58 Bus Coming"
          message: "Your X58 bus to {{ state_attr('sensor.hobart_interchange_bus_route', 'destination') }} departs in {{ states('sensor.hobart_interchange_time_to_departure') }} minutes!"
```

### Filter by Destination Using Templates

```yaml
# Template sensor to track only buses going to University
template:
  - sensor:
      - name: "University Buses"
        state: >
          {% set departures = state_attr('sensor.hobart_interchange_next_bus_departure', 'all_departures') %}
          {% if departures %}
            {% set uni_buses = departures | selectattr('destination', 'search', 'University') | list %}
            {{ uni_buses | length }}
          {% else %}
            0
          {% endif %}
        attributes:
          next_university_bus: >
            {% set departures = state_attr('sensor.hobart_interchange_next_bus_departure', 'all_departures') %}
            {% if departures %}
              {% set uni_buses = departures | selectattr('destination', 'search', 'University') | list %}
              {{ uni_buses[0] if uni_buses else 'None' }}
            {% endif %}
```

## API Information

This integration uses Tasmania's public transport API:
- **Base URL**: `https://real-time.transport.tas.gov.au/timetable/rest`
- **Endpoint**: `/stopdisplays/{stop_id}` 
- **Update Frequency**: 1 minute (20 seconds when buses approach)

The integration automatically fetches stop names from the API, so you'll see friendly names like "Hobart Interchange, Elizabeth St, Stop D3" instead of just the stop ID.

## Data Structure

The integration exposes all upcoming departures in a structured format, making it easy to filter and automate based on:
- Specific bus routes (e.g., only X58 buses)
- Destinations (e.g., only buses to University)  
- Departure times (e.g., buses leaving in the next 10 minutes)
- Platform codes (e.g., only buses from Stop D3)

This unopinionated approach gives you full control over how you want to use the transit data.

## 📋 Examples

Comprehensive examples are available in the [`/examples`](./examples/) directory:

- **[Mushroom Cards](./examples/mushroom-cards.yaml)** - Beautiful dashboard cards with destination filtering, color-coded urgency, and route-specific displays
- **[Automations](./examples/automations.yaml)** - Smart notifications for departures, delays, cancellations, and commute helpers  
- **[Template Sensors](./examples/template-sensors.yaml)** - Advanced filtering for University buses, express services, delayed services, and more

### Quick Example - Configurable Destination Card

**🎯 One-Line Customization**: Just change `'Geeveston'` to your destination!

```yaml
type: custom:mushroom-template-card
primary: >-
  {% set destination = 'Geeveston' %}  # ← Change this line!
  Buses to {{ destination }}
secondary: >-
  {% set destination = 'Geeveston' %}  # ← And this one!
  {% set departures = state_attr('sensor.your_stop_next_bus_departure', 'all_departures') %}
  {% set buses = departures | selectattr('destination', 'search', destination) | list %}
  {% if buses %}
    Route {{ buses[0].line_number }} in {{ buses[0].estimated_minutes_until or buses[0].scheduled_minutes_until }} min
  {% else %}
    No buses to {{ destination }}
  {% endif %}
# ... (see examples directory for complete configuration)
```

**[📁 View All Examples →](./examples/)**

## Support

For issues and feature requests, please visit the [GitHub repository](https://github.com/user/tas-transit).

## License

This project is licensed under the MIT License - see the LICENSE file for details.