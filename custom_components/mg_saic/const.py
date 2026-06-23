# File: const.py

import logging
import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from datetime import timedelta
from enum import Enum
from typing import Union

LOGGER = logging.getLogger(__package__)

DOMAIN = "mg_saic"

# API Base Urls
REGION_BASE_URIS = {
    "EU": "https://gateway-mg-eu.soimt.com/api.app/v1/",
    "China": "https://tap-cn.soimt.com/api.app/v1/",
    "Australia": "https://gateway-mg-au.soimt.com/api.app/v1/",
    "Israel": "https://gateway-mg-il.soimt.com/api.app/v1/",
    "Turkey": "https://gateway-mg-tr.soimt.com/api.app/v1/",
    "India": "https://gateway-mg-in.soimt.com/api.app/v1/",
    "Rest of World": "https://gateway-mg-eu.soimt.com/api.app/v1/",
}

# List of regions for selection in the config flow
REGION_CHOICES = list(REGION_BASE_URIS.keys())

# Phone Login Country Codes
COUNTRY_CODES = [
    {"code": "+1", "country": "USA"},
    {"code": "+7", "country": "Russia"},
    {"code": "+20", "country": "Egypt"},
    {"code": "+27", "country": "South Africa"},
    {"code": "+30", "country": "Greece"},
    {"code": "+31", "country": "Netherlands"},
    {"code": "+32", "country": "Belgium"},
    {"code": "+33", "country": "France"},
    {"code": "+34", "country": "Spain"},
    {"code": "+36", "country": "Hungary"},
    {"code": "+39", "country": "Italy"},
    {"code": "+40", "country": "Romania"},
    {"code": "+41", "country": "Switzerland"},
    {"code": "+43", "country": "Austria"},
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
    {"code": "+64", "country": "New Zealand"},
    {"code": "+65", "country": "Singapore"},
    {"code": "+66", "country": "Thailand"},
    {"code": "+81", "country": "Japan"},
    {"code": "+82", "country": "South Korea"},
    {"code": "+86", "country": "China"},
    {"code": "+90", "country": "Turkey"},
    {"code": "+91", "country": "India"},
    {"code": "+351", "country": "Portugal"},
    {"code": "+355", "country": "Albania"},
    {"code": "+357", "country": "Cyprus"},
    {"code": "+358", "country": "Finland"},
    {"code": "+359", "country": "Bulgaria"},
    {"code": "+370", "country": "Lithuania"},
    {"code": "+371", "country": "Latvia"},
    {"code": "+372", "country": "Estonia"},
    {"code": "+373", "country": "Moldova"},
    {"code": "+385", "country": "Croatia"},
    {"code": "+386", "country": "Slovenia"},
    {"code": "+387", "country": "Bosnia and Herzegovina"},
    {"code": "+389", "country": "North Macedonia"},
    {"code": "+420", "country": "Czech Republic"},
    {"code": "+421", "country": "Slovakia"},
    {"code": "+381", "country": "Serbia"},
    {"code": "+382", "country": "Montenegro"},
    {"code": "+354", "country": "Iceland"},
    {"code": "+353", "country": "Ireland"},
    {"code": "+380", "country": "Ukraine"},
    {"code": "+596", "country": "Martinique"},
    {"code": "+852", "country": "Hong Kong"},
    {"code": "+966", "country": "Saudi Arabia"},
    {"code": "+971", "country": "United Arab Emirates"},
    {"code": "+972", "country": "Israel"},
]

# Conversion factors
PRESSURE_TO_BAR = 0.04
DATA_DECIMAL_CORRECTION = 0.1
DATA_DECIMAL_CORRECTION_SOC = 0.1
DATA_100_DECIMAL_CORRECTION = 0.01

# Conversion factors for charging data
CHARGING_CURRENT_FACTOR = 0.05
CHARGING_VOLTAGE_FACTOR = 0.25

# Per-vehicle-series profiles.
#
# The SAIC API exposes some values (notably AC temperature index scale and
# totalBatteryCapacity) inconsistently or unreliably across models, so these
# are tracked here per series rather than trusted from the API response.
# Series codes come from VinInfo.series (e.g. "EH32SP3", "MIS3E S") and are
# matched as a substring, consistent with the existing detection pattern.
#
# Fields:
#   min_temp / max_temp / temp_offset: AC temperature index mapping. See
#       MGSAICDataUpdateCoordinator.get_ac_temperature_idx for usage.
#   battery_capacity_kwh: known-good usable battery capacity in kWh, used to
#       override the API's totalBatteryCapacity field when it is known to be
#       inaccurate. None means "trust the API value" (no override).
#
# Sources: EH32 (MG4 Electric) values were already present in this codebase
# prior to this table's introduction. MIS3E (MGS6 EV) values confirmed
# against MG UK's official spec sheet and cross-referenced with EV Database,
# electrive.com, and Carwow (77 kWh gross / 74.3 kWh usable, same across
# single-motor Long Range and Dual Motor variants).
VEHICLE_PROFILES = {
    "EH32": {  # MG4 Electric
        "min_temp": 17,
        "max_temp": 33,
        "temp_offset": 3,
        "battery_capacity_kwh": None,
    },
    "MIS3E": {  # MGS6 EV (Long Range and Dual Motor)
        "min_temp": 16,
        "max_temp": 28,
        "temp_offset": 2,
        "battery_capacity_kwh": 74.3,
    },
}

# Fallback profile used when the vehicle's series does not match any entry
# in VEHICLE_PROFILES above (e.g. MG5, ZS EV, or any model not yet profiled).
DEFAULT_VEHICLE_PROFILE = {
    "min_temp": 16,
    "max_temp": 28,
    "temp_offset": 2,
    "battery_capacity_kwh": None,
}

# Base update intervals
# UPDATE_INTERVAL is the idle/parked background refresh — a safety net to keep
# data from going completely stale.  Now that the SAICMGAccountPoller triggers
# an immediate refresh on engine-start, shutdown, and charging events, this
# interval only matters when the car is genuinely sitting idle with nothing
# happening.  30 minutes is a good balance: fresh enough to be useful, infrequent
# enough not to drain the 12V battery or hit API rate limits.
# Users can still override this lower via the integration options if they prefer.
UPDATE_INTERVAL = timedelta(minutes=30)
UPDATE_INTERVAL_CHARGING = timedelta(minutes=5)
UPDATE_INTERVAL_POWERED = timedelta(minutes=15)

# Additional Update Intervals
UPDATE_INTERVAL_AFTER_SHUTDOWN = timedelta(minutes=2)
UPDATE_INTERVAL_GRACE_PERIOD = timedelta(minutes=10)

# After action immediate and refresh intervals
AFTER_ACTION_UPDATE_INTERVAL_DELAY = timedelta(seconds=15)

# Default additional long-interval updates after actions
DEFAULT_ALARM_LONG_INTERVAL = timedelta(minutes=5)
DEFAULT_AC_LONG_INTERVAL = timedelta(minutes=15)
DEFAULT_FRONT_DEFROST_LONG_INTERVAL = timedelta(minutes=15)
DEFAULT_REAR_WINDOW_HEAT_LONG_INTERVAL = timedelta(minutes=15)
DEFAULT_LOCK_UNLOCK_LONG_INTERVAL = timedelta(minutes=5)
DEFAULT_CHARGING_PORT_LOCK_LONG_INTERVAL = timedelta(minutes=5)
DEFAULT_HEATED_SEATS_LONG_INTERVAL = timedelta(minutes=15)
DEFAULT_BATTERY_HEATING_LONG_INTERVAL = timedelta(minutes=15)
DEFAULT_CHARGING_LONG_INTERVAL = timedelta(minutes=5)
DEFAULT_SUNROOF_LONG_INTERVAL = timedelta(minutes=5)
DEFAULT_TAILGATE_LONG_INTERVAL = timedelta(minutes=5)
DEFAULT_TARGET_SOC_LONG_INTERVAL = timedelta(minutes=5)
DEFAULT_CHARGING_CURRENT_LONG_INTERVAL = timedelta(minutes=5)

# Configuration Options
CONF_HAS_SUNROOF = "has_sunroof"
CONF_HAS_HEATED_SEATS = "has_heated_seats"
CONF_HAS_BATTERY_HEATING = "has_battery_heating"
CONF_HAS_STEERING_WHEEL_HEAT = "has_steering_wheel_heat"

# Generic response tresholds
GENERIC_RESPONSE_SOC_THRESHOLD = 1000
GENERIC_RESPONSE_STATUS_THRESHOLD = 0
GENERIC_RESPONSE_TEMPERATURE = -40
GENERIC_RESPONSE_EXTREME_TEMPERATURE = -128

# Sanity bounds for the API's statusTime field. A response whose timestamp
# falls outside these bounds relative to "now" is treated as untrustworthy
# and discarded (see SAICMGDataUpdateCoordinator._is_status_timestamp_valid).
STATUS_TIMESTAMP_FUTURE_TOLERANCE = timedelta(minutes=5)
STATUS_TIMESTAMP_MAX_AGE = timedelta(hours=24)

# Retry configuration
RETRY_LIMIT = 5
RETRY_BACKOFF_FACTOR = 15

# Charging status codes indicating that the vehicle is actively using the
# charging/discharging system.  Used by the coordinator to select the
# charging update interval and keep the session alive.
# 13 = V2X_DISCHARGING — included so V2X export sessions get the same
# frequent refresh cadence as AC/DC charging sessions.
CHARGING_STATUS_CODES = {1, 3, 10, 12, 13}

# Charging Current Limit options
CHARGING_CURRENT_OPTIONS = ["0A (Ignore)", "6A", "8A", "16A", "Max"]

# Platforms
PLATFORMS = [
    "binary_sensor",
    "button",
    "climate",
    "device_tracker",
    "event",
    "lock",
    "number",
    "select",
    "sensor",
    "switch",
]


# Battery SOC
class BatterySoc(Enum):
    """Enum for Battery SOC identification"""

    SOC_40 = 1
    SOC_50 = 2
    SOC_60 = 3
    SOC_70 = 4
    SOC_80 = 5
    SOC_90 = 6
    SOC_100 = 7


# Charge Current Limit
class ChargeCurrentLimitOption(Enum):
    C_IGNORE = 0
    C_6A = 1
    C_8A = 2
    C_16A = 3
    C_MAX = 4

    @staticmethod
    def to_code(limit: Union[str, "ChargeCurrentLimitOption"]):
        LOGGER.debug(f"Converting limit: {limit} (type: {type(limit)}) to code")
        if isinstance(limit, ChargeCurrentLimitOption):
            return limit
        if isinstance(limit, str):
            limit_upper = limit.upper()
            match limit_upper:
                case "6A":
                    return ChargeCurrentLimitOption.C_6A
                case "8A":
                    return ChargeCurrentLimitOption.C_8A
                case "16A":
                    return ChargeCurrentLimitOption.C_16A
                case "MAX":
                    return ChargeCurrentLimitOption.C_MAX
                case "0A (IGNORE)":
                    return ChargeCurrentLimitOption.C_IGNORE
                case "0A":
                    return ChargeCurrentLimitOption.C_IGNORE
                case _:
                    LOGGER.error(f"Unknown charge current limit: {limit}")
                    raise ValueError(f"Unknown charge current limit: {limit}")
        LOGGER.error(f"Invalid type for limit: {type(limit)}")
        raise TypeError(f"Invalid type for limit: {type(limit)}")

    @property
    def limit(self) -> str:
        match self:
            case ChargeCurrentLimitOption.C_6A:
                return "6A"
            case ChargeCurrentLimitOption.C_8A:
                return "8A"
            case ChargeCurrentLimitOption.C_16A:
                return "16A"
            case ChargeCurrentLimitOption.C_MAX:
                return "Max"
            case ChargeCurrentLimitOption.C_IGNORE:
                return "0A (Ignore)"
            case _:
                raise ValueError(f"Unknown charge current limit code: {self}")


# Windows List
class VehicleWindowId(Enum):
    """Enum for identifying vehicle windows."""

    DRIVER = "driver"
    WINDOW_2 = "window_2"
    WINDOW_3 = "window_3"
    WINDOW_4 = "window_4"
    SUNROOF = "sunroof"
