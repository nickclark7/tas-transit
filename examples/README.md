# Tasmanian Transport Integration - Examples

This directory contains practical examples for using the Tasmanian Transport Home Assistant integration.

## 📁 Files Overview

- **`mushroom-cards.yaml`** - Mushroom card examples for beautiful dashboard displays
- **`automations.yaml`** - Automation examples for notifications and smart home triggers  
- **`template-sensors.yaml`** - Template sensors for advanced data filtering and processing

## 🚀 Quick Start

1. **Replace Entity IDs**: In all examples, replace `sensor.your_stop_next_bus_departure` with your actual sensor entity ID
2. **One-Line Customization**: Look for `{% set destination = 'University' %}` lines and change the destination to match your needs
3. **Adjust Timings**: Modify time thresholds to suit your preferences (e.g., 10 minutes warning vs 15 minutes)

### 🎯 Super Easy Configuration
Many examples now use a **single variable at the top**. Just change this one line:
```yaml
{% set destination = 'Geeveston' %}  # ← Change this!
```
And the entire card/automation updates automatically!

## 🍄 Mushroom Cards

### Featured Examples:
- **🎯 Configurable Destination Card** - One-line customization for any destination (Geeveston → Your town)
- **🎯 Multi-Bus Display** - Shows multiple buses with one-line destination change
- **🎯 Simple Entity Card** - Clean entity card with destination filtering
- **🎯 Detailed Entity List** - Shows all departures in a list format with filtering
- **Route-Specific** - Filter by route number (e.g., X58 Express)
- **Generic Template** - Easy to customize for any destination

### Icon Colors:
- 🔴 **Red**: ≤5 minutes (urgent)
- 🟠 **Orange**: ≤15 minutes (soon)  
- 🟢 **Green**: >15 minutes (plenty of time)
- ⚫ **Grey**: No buses found

## 🤖 Automations

### Featured Examples:
- **Basic Departure Reminder** - Alert when any bus is 10 minutes away
- **Route-Specific Alerts** - Only notify for specific routes (X58, etc.)
- **Destination Filtering** - Alert only for buses to University, City, etc.
- **Multi-Stop Monitoring** - Track buses from multiple stops
- **Commute Helper** - Weekday morning-only alerts
- **Cancellation Alerts** - Know when buses are cancelled
- **Weekend Service** - Different timing for weekend buses

## 📊 Template Sensors

### Featured Examples:
- **🎯 Configurable Destination Counter** - One-line customization for any destination (University → Your destination)
- **Express Services** - Track only X-series express routes
- **Departing Soon** - Buses leaving in next 15 minutes
- **Peak Hour Indicator** - Detect peak service periods
- **Platform-Specific** - Filter by platform code (D3, etc.)
- **Delayed Services** - Track buses running >5 minutes late

## 💡 Customization Tips

### Change Destinations
Replace destination filters throughout:
```yaml
# From:
selectattr('destination', 'search', 'Geeveston')
# To:
selectattr('destination', 'search', 'Sandy Bay')
```

### Modify Time Thresholds
Adjust warning times:
```yaml
# From: 10 minute warning
below: 10
# To: 15 minute warning  
below: 15
```

### Filter by Route Number
```yaml
# Specific route
selectattr('line_number', 'eq', '401')
# Express routes only
selectattr('line_number', 'match', '^X')
```

### Multiple Criteria
```yaml
# University buses on routes 501 or 601
{% set uni_buses = departures | 
   selectattr('destination', 'search', 'University') | 
   selectattr('line_number', 'in', ['501', '601']) | 
   list %}
```

## 🎨 Dashboard Integration

### Mushroom Card Installation
1. Install [Mushroom Cards](https://github.com/piitaya/lovelace-mushroom) via HACS
2. Copy desired card YAML from `mushroom-cards.yaml`
3. Paste into your dashboard in raw configuration mode
4. Update entity IDs and customize as needed

### Template Sensor Setup
1. Add examples from `template-sensors.yaml` to your `configuration.yaml`
2. Place under the `template:` section
3. Restart Home Assistant
4. New sensors will appear as `sensor.university_buses_count`, etc.

## 🔧 Troubleshooting

### Common Issues:
- **"Unknown" entity states**: Check your sensor entity ID is correct
- **No data in templates**: Ensure the integration is working and has departure data
- **Cards not updating**: Verify sensors are updating (check in Developer Tools)

### Testing Templates:
Use Developer Tools > Templates to test your Jinja2 templates before adding to cards or sensors.

## 📋 Entity ID Examples

Your sensor entity IDs will look like:
- `sensor.hobart_interchange_next_bus_departure`
- `sensor.elizabeth_street_mall_time_to_departure`  
- `sensor.sandy_bay_shopping_centre_bus_route`

Find your exact entity IDs in **Developer Tools > States** or by looking at the integration in **Settings > Devices & Services**.