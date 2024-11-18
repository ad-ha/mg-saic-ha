import logging
from datetime import timedelta

LOGGER = logging.getLogger(__package__)

DOMAIN = "mg_saic"

# Conversion factors
PRESSURE_TO_BAR = 0.04
DATA_DECIMAL_CORRECTION = 0.1
DATA_DECIMAL_CORRECTION_SOC = 0.1
DATA_100_DECIMAL_CORRECTION = 0.01

# Conversion factors for charging data
CHARGING_CURRENT_FACTOR = 0.001
CHARGING_VOLTAGE_FACTOR = 0.145

# API Base Urls
REGION_BASE_URIS = {
    "EU": "https://gateway-mg-eu.soimt.com/api.app/v1/",
    "China": "https://tap-cn.soimt.com/api.app/v1/",
    "Rest of World": "https://gateway-mg-eu.soimt.com/api.app/v1/",
    "Australia": "https://gateway-mg-au.soimt.com/api.app/v1/",
}

# List of regions for selection in the config flow
REGION_CHOICES = list(REGION_BASE_URIS.keys())

# Phone Login Country Codes
COUNTRY_CODES = [
    {"code": "+1", "country": "USA"},
    {"code": "+7", "country": "Russia"},
    {"code": "+20", "country": "Egypt"},
    {"code": "+27", "country": "South Africa"},
    {"code": "+31", "country": "Netherlands"},
    {"code": "+32", "country": "Belgium"},
    {"code": "+33", "country": "France"},
    {"code": "+34", "country": "Spain"},
    {"code": "+39", "country": "Italy"},
    {"code": "+41", "country": "Switzerland"},
    {"code": "+44", "country": "United Kingdom"},
    {"code": "+45", "country": "Denmark"},
    {"code": "+46", "country": "Sweden"},
    {"code": "+47", "country": "Norway"},
    {"code": "+48", "country": "Poland"},
    {"code": "+49", "country": "Germany"},
    {"code": "+52", "country": "Mexico"},
    {"code": "+53", "country": "Cuba"},
    {"code": "+54", "country": "Argentina"},
    {"code": "+55", "country": "Brazil"},
    {"code": "+56", "country": "Chile"},
    {"code": "+57", "country": "Colombia"},
    {"code": "+58", "country": "Venezuela"},
    {"code": "+60", "country": "Malaysia"},
    {"code": "+61", "country": "Australia"},
    {"code": "+62", "country": "Indonesia"},
    {"code": "+63", "country": "Philippines"},
    {"code": "+65", "country": "Singapore"},
    {"code": "+66", "country": "Thailand"},
    {"code": "+81", "country": "Japan"},
    {"code": "+82", "country": "South Korea"},
    {"code": "+86", "country": "China"},
    {"code": "+90", "country": "Turkey"},
    {"code": "+91", "country": "India"},
    {"code": "+351", "country": "Portugal"},
    {"code": "+420", "country": "Czech Republic"},
    {"code": "+966", "country": "Saudi Arabia"},
    {"code": "+971", "country": "United Arab Emirates"},
]

# Update Settings
DEFAULT_SCAN_INTERVAL = timedelta(minutes=120)
DEFAULT_CHARGING_SCAN_INTERVAL = timedelta(minutes=10)

UPDATE_INTERVAL = DEFAULT_SCAN_INTERVAL
UPDATE_INTERVAL_CHARGING = DEFAULT_CHARGING_SCAN_INTERVAL

# Generic response tresholds
GENERIC_RESPONSE_SOC_THRESHOLD = 1000
GENERIC_RESPONSE_STATUS_THRESHOLD = 0

# Retry configuration
RETRY_LIMIT = 5
MAX_RETRY_DELAY = 60
RETRY_BACKOFF_FACTOR = 15

# Charging status codes indicating that the vehicle is charging
CHARGING_STATUS_CODES = {1, 3, 10, 12}

# Platforms
PLATFORMS = [
    "sensor",
    "binary_sensor",
    "device_tracker",
    "button",
    "climate",
    "number",
    "switch",
    "lock",
]
