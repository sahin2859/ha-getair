# getAir Home Assistant Integration

A custom Home Assistant integration for getAir smart ventilation systems (ComfortControl Pro / ComfortControl Pro BT).

Made entirely by Claude.

## Installation

### HACS (recommended) (will do someday)
1. Add this repo as a custom HACS repository
2. Install "getAir Ventilation"
3. Restart Home Assistant

### Manual
1. Copy the `custom_components/getair/` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

## Setup
1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **getAir**
3. Enter your getAir account email and password

## Entities

### Climate (`climate.DEVICE_NAME`)
- Set **target temperature**
- Switch **ventilation mode** via presets:
  - Normal Ventilation
  - Inverse Ventilation
  - Heat Recovery
  - Night Mode
  - Boost
  - Inverse Boost
  - Boost with Heat Recovery
  - Auto

### Fan (`fan.DEVICE_NAME_fan`)
- Turn on/off
- Set speed via **percentage** (maps to getAir speed 0.5–4.0)

### Time Profile (`select.DEVICE_NAME_time_profile`)
- Select time profiles set in the app (Arbeitswoche | Freizeitwoche | Sommer) 

### Sensors
| Sensor | Description |
|--------|-------------|
| Indoor Temperature | Current indoor temp (°C) |
| Indoor Humidity | Current indoor humidity (%) |
| Outdoor Temperature | Outdoor temp (°C) |
| Outdoor Humidity | Outdoor humidity (%) |
| Indoor Air Quality | IAQ index (0–500) (Returns Unknown)|
| Air Pressure | hPa |
| Fan Speed | Raw speed value (0–4) |
| Runtime | Total runtime (hours) |
| Ventilation Mode | Current active mode |
| Firmware Version | Installed firmware |

## Notes
- Data refreshes every 60 seconds (to prevent throttling)
- Auth token is valid for 24 hours; the integration auto-refreshes it
- Compatible devices: **ComfortControl Pro** and **ComfortControl Pro BT**
- Credits to getAir for providing the API https://github.com/getaireu/REST-API
- Credits to Claude for writing the Home Assistant Integration
