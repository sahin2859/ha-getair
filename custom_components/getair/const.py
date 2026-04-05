"""Constants for getAir integration."""

DOMAIN = "getair"

AUTH_URL = "https://auth.getair.eu"
API_URL = "https://be01.ga-cc.de"
CLIENT_ID = "7jPuzDmLiKFF6oPtvsFUhBkyPahA7Lh5"

# Ventilation modes
MODES = {
    "ventilate": "Normal Ventilation",
    "ventilate_inv": "Inverse Ventilation",
    "ventilate_hr": "Heat Recovery",
    "night": "Night Mode",
    "rush": "Boost",
    "rush_inv": "Inverse Boost",
    "rush_hr": "Boost with Heat Recovery",
    "auto": "Auto",
}

# Fan speed range
SPEED_MIN = 0.5
SPEED_MAX = 4.0
SPEED_STEP = 0.5

CONF_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"
