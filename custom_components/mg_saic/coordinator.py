# File: coordinator.py

from datetime import datetime, timedelta, timezone
import asyncio
from contextlib import suppress
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import utcnow
from .api import SAICMGAPIClient
from .logic import select_update_interval

# ── Message-driven update constants ─────────────────────────────────────────
# How often to poll the SAIC alarm message queue (seconds).
# 60s matches the MQTT gateway default; the message queue is lightweight —
# it queries SAIC's server, not the car's telematics module directly.
MESSAGE_POLL_INTERVAL_SECONDS = 60

# messageType string that indicates a vehicle start / engine-on event.
# Confirmed from saic-python-mqtt-gateway source (messageType "323").
MESSAGE_TYPE_VEHICLE_START = "323"

# Keywords in message title/content indicating vehicle shutdown (offCar).
# The new REST API does not expose a distinct messageType for shutdown,
# so we infer from message text.
SHUTDOWN_TITLE_KEYWORDS = [
    "vehicle off", "car off", "turned off", "engine off", "ignition off",
    "vehicle stopped", "parked",
]

# Keywords indicating a charging / plug-in event.
CHARGING_TITLE_KEYWORDS = [
    "charging", "charge", "plugged", "connected to charger",
    "charging started", "ev connected",
]

# After the car turns off, fire extra refreshes at these intervals (seconds)
# to catch plug-in as quickly as possible. The coordinator is still on its
# 15-min powered poll cycle when shutdown occurs, so without this we'd wait
# up to 15 minutes before detecting plug-in.
# The sequence exits early as soon as is_charging is detected, so a long
# sequence costs nothing if you plug in quickly.
# Sequence: 1min, 3min, 7min, 15min, 25min → catches plug-in within ~1-25 minutes.
POST_SHUTDOWN_REFRESH_SEQUENCE = [60, 120, 240, 480, 600]
from .const import (
    AFTER_ACTION_UPDATE_INTERVAL_DELAY,
    CHARGING_STATUS_CODES,
    DEFAULT_AC_LONG_INTERVAL,
    DEFAULT_ALARM_LONG_INTERVAL,
    DEFAULT_BATTERY_HEATING_LONG_INTERVAL,
    DEFAULT_CHARGING_CURRENT_LONG_INTERVAL,
    DEFAULT_CHARGING_LONG_INTERVAL,
    DEFAULT_CHARGING_PORT_LOCK_LONG_INTERVAL,
    DEFAULT_FRONT_DEFROST_LONG_INTERVAL,
    DEFAULT_HEATED_SEATS_LONG_INTERVAL,
    DEFAULT_LOCK_UNLOCK_LONG_INTERVAL,
    DEFAULT_REAR_WINDOW_HEAT_LONG_INTERVAL,
    DEFAULT_SUNROOF_LONG_INTERVAL,
    DEFAULT_TAILGATE_LONG_INTERVAL,
    DEFAULT_TARGET_SOC_LONG_INTERVAL,
    DOMAIN,
    GENERIC_RESPONSE_SOC_THRESHOLD,
    GENERIC_RESPONSE_STATUS_THRESHOLD,
    GENERIC_RESPONSE_TEMPERATURE,
    LOGGER,
    RETRY_BACKOFF_FACTOR,
    RETRY_LIMIT,
    UPDATE_INTERVAL,
    UPDATE_INTERVAL_AFTER_SHUTDOWN,
    UPDATE_INTERVAL_CHARGING,
    UPDATE_INTERVAL_GRACE_PERIOD,
    UPDATE_INTERVAL_POWERED,
)


class SAICMGDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the MG SAIC API."""

    def __init__(self, hass, client: SAICMGAPIClient, config_entry):
        """Initialize."""
        super().__init__(
            hass,
            LOGGER,
            name="MG SAIC data update coordinator",
            update_interval=UPDATE_INTERVAL,
        )

        self.client = client
        self.config_entry = config_entry
        self.vin = config_entry.data.get("vin")

        # State Variables
        self.is_charging = False
        self.is_powered_on = False
        self.is_initial_setup = False
        self.in_grace_period = False
        self.after_shutdown_active = False

        # Activity Tracking
        self.last_powered_on_time = None
        self.last_powered_off_time = None
        self.last_vehicle_activity = None

        # Next Update Time
        self.next_update_time = None
        self._action_refresh_task = None
        self._action_refresh_generation = 0

        # Message queue polling state
        self._message_poll_task: asyncio.Task | None = None
        self._last_seen_message_id: str | int | None = None
        self._last_seen_message_ts = None

        # Post-shutdown rapid refresh state
        self._shutdown_refresh_task: asyncio.Task | None = None

        # Track previous powered-on state so we detect the transition even
        # when status_data is None (generic response during power-down)
        self._prev_is_powered_on: bool = False

        # Initialize with default values
        self.vehicle_series = None
        self.min_temp = 16  # Default fallback
        self.max_temp = 28  # Default fallback
        self.temp_offset = 2  # Default fallback

        # Initialize update intervals from config_entry options, falling back to defaults if not set
        options = config_entry.options

        # Helper function to get interval from options or fallback to const.py
        def get_interval(option_key, default_interval):
            return timedelta(
                minutes=options.get(
                    option_key, int(default_interval.total_seconds() / 60)
                )
            )

        def get_delay(option_key, default_interval):
            return timedelta(
                seconds=options.get(option_key, int(default_interval.total_seconds()))
            )

        # Base update intervals
        self.default_update_interval = get_interval("update_interval", UPDATE_INTERVAL)
        self.update_interval = self.default_update_interval
        self.charging_update_interval = get_interval(
            "charging_update_interval", UPDATE_INTERVAL_CHARGING
        )
        self.powered_update_interval = get_interval(
            "powered_update_interval", UPDATE_INTERVAL_POWERED
        )

        # Additional update intervals
        self.after_shutdown_update_interval = get_interval(
            "after_shutdown_update_interval", UPDATE_INTERVAL_AFTER_SHUTDOWN
        )
        self.grace_period_update_interval = get_interval(
            "grace_period_update_interval", UPDATE_INTERVAL_GRACE_PERIOD
        )

        # After action immediate and refresh intervals
        self.after_action_delay = get_delay(
            "after_action_delay", AFTER_ACTION_UPDATE_INTERVAL_DELAY
        )

        # Long-interval updates after actions
        self.alarm_long_interval = get_interval(
            "alarm_long_interval", DEFAULT_ALARM_LONG_INTERVAL
        )
        self.ac_long_interval = get_interval(
            "ac_long_interval", DEFAULT_AC_LONG_INTERVAL
        )
        self.front_defrost_long_interval = get_interval(
            "front_defrost_long_interval", DEFAULT_FRONT_DEFROST_LONG_INTERVAL
        )
        self.rear_window_heat_long_interval = get_interval(
            "rear_window_heat_long_interval", DEFAULT_REAR_WINDOW_HEAT_LONG_INTERVAL
        )
        self.lock_unlock_long_interval = get_interval(
            "lock_unlock_long_interval", DEFAULT_LOCK_UNLOCK_LONG_INTERVAL
        )
        self.charging_port_lock_long_interval = get_interval(
            "charging_port_lock_long_interval", DEFAULT_CHARGING_PORT_LOCK_LONG_INTERVAL
        )
        self.heated_seats_long_interval = get_interval(
            "heated_seats_long_interval", DEFAULT_HEATED_SEATS_LONG_INTERVAL
        )
        self.battery_heating_long_interval = get_interval(
            "battery_heating_long_interval", DEFAULT_BATTERY_HEATING_LONG_INTERVAL
        )
        self.charging_long_interval = get_interval(
            "charging_long_interval", DEFAULT_CHARGING_LONG_INTERVAL
        )
        self.sunroof_long_interval = get_interval(
            "sunroof_long_interval", DEFAULT_SUNROOF_LONG_INTERVAL
        )
        self.tailgate_long_interval = get_interval(
            "tailgate_long_interval", DEFAULT_TAILGATE_LONG_INTERVAL
        )
        self.target_soc_long_interval = get_interval(
            "target_soc_long_interval", DEFAULT_TARGET_SOC_LONG_INTERVAL
        )
        self.charging_current_long_interval = get_interval(
            "charging_current_long_interval", DEFAULT_CHARGING_CURRENT_LONG_INTERVAL
        )

        LOGGER.debug(
            f"Update intervals initialized: "
            f"Default: {self.default_update_interval}, "
            f"Charging: {self.charging_update_interval}, "
            f"Powered: {self.powered_update_interval}, "
            f"After Shutdown: {self.after_shutdown_update_interval}, "
            f"Grace Period: {self.grace_period_update_interval}, "
            f"After Action Delay: {self.after_action_delay}"
        )

        # Use the vehicle type from the config entry
        self.vehicle_type = self.config_entry.data.get("vehicle_type")

        # Vehicle capabilities
        self.has_sunroof = config_entry.options.get(
            "has_sunroof", config_entry.data.get("has_sunroof", False)
        )
        self.has_heated_seats = config_entry.options.get(
            "has_heated_seats", config_entry.data.get("has_heated_seats", False)
        )
        self.has_battery_heating = config_entry.options.get(
            "has_battery_heating", config_entry.data.get("has_battery_heating", False)
        )

    # Update Options
    async def async_update_options(self, options):
        """Update options and reschedule refresh."""

        # Helper functions to get intervals
        def get_interval(option_key, default_interval):
            """Retrieve interval in minutes from options or fallback to default."""
            return timedelta(
                minutes=options.get(
                    option_key, int(default_interval.total_seconds() / 60)
                )
            )

        def get_delay(option_key, default_interval):
            """Retrieve delay in seconds from options or fallback to default."""
            return timedelta(
                seconds=options.get(option_key, int(default_interval.total_seconds()))
            )

        # Update all update intervals
        self.default_update_interval = get_interval("update_interval", UPDATE_INTERVAL)
        self.update_interval = self.default_update_interval
        self.charging_update_interval = get_interval(
            "charging_update_interval", UPDATE_INTERVAL_CHARGING
        )
        self.powered_update_interval = get_interval(
            "powered_update_interval", UPDATE_INTERVAL_POWERED
        )

        self.after_shutdown_update_interval = get_interval(
            "after_shutdown_update_interval", UPDATE_INTERVAL_AFTER_SHUTDOWN
        )
        self.grace_period_update_interval = get_interval(
            "grace_period_update_interval", UPDATE_INTERVAL_GRACE_PERIOD
        )

        self.after_action_delay = get_delay(
            "after_action_delay", AFTER_ACTION_UPDATE_INTERVAL_DELAY
        )

        # Long-interval updates after actions
        self.alarm_long_interval = get_interval(
            "alarm_long_interval", DEFAULT_ALARM_LONG_INTERVAL
        )
        self.ac_long_interval = get_interval(
            "ac_long_interval", DEFAULT_AC_LONG_INTERVAL
        )
        self.front_defrost_long_interval = get_interval(
            "front_defrost_long_interval", DEFAULT_FRONT_DEFROST_LONG_INTERVAL
        )
        self.rear_window_heat_long_interval = get_interval(
            "rear_window_heat_long_interval", DEFAULT_REAR_WINDOW_HEAT_LONG_INTERVAL
        )
        self.lock_unlock_long_interval = get_interval(
            "lock_unlock_long_interval", DEFAULT_LOCK_UNLOCK_LONG_INTERVAL
        )
        self.charging_port_lock_long_interval = get_interval(
            "charging_port_lock_long_interval", DEFAULT_CHARGING_PORT_LOCK_LONG_INTERVAL
        )
        self.heated_seats_long_interval = get_interval(
            "heated_seats_long_interval", DEFAULT_HEATED_SEATS_LONG_INTERVAL
        )
        self.battery_heating_long_interval = get_interval(
            "battery_heating_long_interval", DEFAULT_BATTERY_HEATING_LONG_INTERVAL
        )
        self.charging_long_interval = get_interval(
            "charging_long_interval", DEFAULT_CHARGING_LONG_INTERVAL
        )
        self.sunroof_long_interval = get_interval(
            "sunroof_long_interval", DEFAULT_SUNROOF_LONG_INTERVAL
        )
        self.tailgate_long_interval = get_interval(
            "tailgate_long_interval", DEFAULT_TAILGATE_LONG_INTERVAL
        )
        self.target_soc_long_interval = get_interval(
            "target_soc_long_interval", DEFAULT_TARGET_SOC_LONG_INTERVAL
        )
        self.charging_current_long_interval = get_interval(
            "charging_current_long_interval", DEFAULT_CHARGING_CURRENT_LONG_INTERVAL
        )

        # Update capabilities from options
        self.has_sunroof = options.get("has_sunroof", self.has_sunroof)
        self.has_heated_seats = options.get("has_heated_seats", self.has_heated_seats)
        self.has_battery_heating = options.get(
            "has_battery_heating", self.has_battery_heating
        )

        LOGGER.debug(
            f"Update intervals updated via options: "
            f"Default: {self.default_update_interval}, "
            f"Charging: {self.charging_update_interval}, "
            f"Powered: {self.powered_update_interval}, "
            f"After Shutdown: {self.after_shutdown_update_interval}, "
            f"Grace Period: {self.grace_period_update_interval}, "
            f"After Action Delay: {self.after_action_delay}, "
            f"Alarm: {self.alarm_long_interval}, "
            f"AC: {self.ac_long_interval}, "
            f"Front Defrost: {self.front_defrost_long_interval}, "
            f"Rear Window Heat: {self.rear_window_heat_long_interval}, "
            f"Lock/Unlock: {self.lock_unlock_long_interval}, "
            f"Charging Port Lock: {self.charging_port_lock_long_interval}, "
            f"Heated Seats: {self.heated_seats_long_interval}, "
            f"Battery Heating: {self.battery_heating_long_interval}, "
            f"Charging: {self.charging_long_interval}, "
            f"Sunroof: {self.sunroof_long_interval}, "
            f"Tailgate: {self.tailgate_long_interval}, "
            f"Target SOC: {self.target_soc_long_interval}, "
            f"Charging Current: {self.charging_current_long_interval}"
        )

        if not getattr(self, "_action_interval_active", False):
            self._adjust_update_interval()
        else:
            self.next_update_time = utcnow() + self.update_interval
            self.async_update_listeners()

    async def async_setup(self):
        """Set up the coordinator."""
        self.is_initial_setup = True
        vin = self.vin

        # Restore last known values for activity and power-off times
        entity_id_last_activity = f"sensor.{DOMAIN}_{self.vin}_last_vehicle_activity"
        entity_id_last_power_off = f"sensor.{DOMAIN}_{self.vin}_last_powered_off"
        entity_id_last_power_on = f"sensor.{DOMAIN}_{self.vin}_last_powered_on"

        last_activity_state = self.hass.states.get(entity_id_last_activity)
        last_power_off_state = self.hass.states.get(entity_id_last_power_off)
        last_power_on_state = self.hass.states.get(entity_id_last_power_on)

        if last_activity_state and last_activity_state.state != "unavailable":
            try:
                self.last_vehicle_activity = datetime.fromisoformat(
                    last_activity_state.state
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                self.last_vehicle_activity = datetime.now(timezone.utc) - timedelta(
                    hours=24
                )
                LOGGER.warning(
                    f"Invalid last_vehicle_activity format: {last_activity_state.state}. Falling back to default."
                )
        else:
            self.last_vehicle_activity = datetime.now(timezone.utc) - timedelta(
                hours=24
            )

        if last_power_off_state and last_power_off_state.state != "unavailable":
            try:
                self.last_powered_off_time = datetime.fromisoformat(
                    last_power_off_state.state
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                self.last_powered_off_time = datetime.now(timezone.utc) - timedelta(
                    hours=24
                )
                LOGGER.warning(
                    f"Invalid last_powered_off format: {last_power_off_state.state}. Falling back to default."
                )
        else:
            self.last_powered_off_time = datetime.now(timezone.utc) - timedelta(
                hours=24
            )

        if last_power_on_state and last_power_on_state.state != "unavailable":
            try:
                self.last_powered_on_time = datetime.fromisoformat(
                    last_power_on_state.state
                ).replace(tzinfo=timezone.utc)
            except ValueError:
                self.last_powered_on_time = datetime.now(timezone.utc) - timedelta(
                    hours=24
                )
                LOGGER.warning(
                    f"Invalid last_powered_on format: {last_power_on_state.state}. Falling back to default."
                )
        else:
            self.last_powered_on_time = datetime.now(timezone.utc) - timedelta(hours=24)

        try:
            await self.async_config_entry_first_refresh()
        except Exception as e:
            LOGGER.error("First data update failed: %s", e)
            # Proceed anyway, set data to empty dict
            self.data = {}

        if "info" in self.data and self.data["info"]:
            # Find the vehicle info matching the current VIN
            vin_info = next(
                (v for v in self.data.get("info", []) if v.vin == vin), None
            )

            if not vin_info:
                LOGGER.error(f"No vehicle data found for VIN: {vin}")
                raise UpdateFailed("No matching vehicle data found.")

            # Store the matching vehicle info
            self.vin_info = vin_info

            # Get vehicle series from API response
            self.vehicle_series = getattr(vin_info, "series", "").upper()

            # Set temperature range based on vehicle series
            if "EH32" in self.vehicle_series:
                self.min_temp = 17
                self.max_temp = 33
                self.temp_offset = 3
            else:  # For other models like MG5, ZS EV, etc.
                self.min_temp = 16
                self.max_temp = 28
                self.temp_offset = 2

            LOGGER.debug(
                f"Vehicle series detected: {self.vehicle_series}. "
                f"Temperature range: {self.min_temp}-{self.max_temp}°C, "
                f"Offset: {self.temp_offset}"
            )
        else:
            LOGGER.error(f"No 'info' data found for VIN: {vin}")
            raise UpdateFailed("No 'info' data found for VIN.")

        # Update capabilities from options
        self.has_sunroof = self.config_entry.options.get(
            "has_sunroof", self.has_sunroof
        )
        self.has_heated_seats = self.config_entry.options.get(
            "has_heated_seats", self.has_heated_seats
        )
        self.has_battery_heating = self.config_entry.options.get(
            "has_battery_heating", self.has_battery_heating
        )

        self.is_initial_setup = False

        # Register alarm switches so SAIC server queues event messages for us
        await self.client.set_alarm_switches(vin=self.vin)

        # Start the background message-queue polling loop
        await self._start_message_polling()

        return True

    async def _async_update_data(self):
        """Fetch data from the API."""
        data = {}

        # Fetch vehicle info with retries
        data["info"] = (
            await self._fetch_with_retries(
                self.client.get_vehicle_info,
                self._is_generic_response_vehicle_info,
                "vehicle info",
            )
            or []
        )

        if not data["info"]:
            raise UpdateFailed("Cannot proceed without vehicle info.")

        vin = self.config_entry.data.get("vin")
        filtered_info = [v for v in data["info"] if v.vin == vin]
        if not filtered_info:
            raise UpdateFailed(f"No data found for VIN: {vin}")

        # Overwrite info with the filtered result and store it in an attribute
        data["info"] = filtered_info
        self.vin_info = filtered_info[0]

        if not filtered_info:
            raise UpdateFailed(f"No data found for VIN: {vin}")

        # Fetch vehicle status with retries
        data["status"] = await self._fetch_with_retries(
            self.client.get_vehicle_status,
            self._is_generic_response_vehicle_status,
            "vehicle status",
        )

        # Fetch charging info with retries
        if self.vehicle_type in ["BEV", "PHEV"]:
            data["charging"] = await self._fetch_with_retries(
                self.client.get_charging_info,
                self._is_generic_response_charging,
                "charging info",
            )

        # Determine charging status
        self.is_charging = False
        if data.get("charging") is not None:
            chrg_data = getattr(data["charging"], "chrgMgmtData", None)
            if chrg_data is not None:
                bms_chrg_sts = getattr(chrg_data, "bmsChrgSts", None)
                self.is_charging = bms_chrg_sts in CHARGING_STATUS_CODES
        else:
            LOGGER.debug("Charging data not available.")

        # Update internal state variables
        self._update_state(data)

        # Adjust update intervals dynamically
        self._adjust_update_interval()

        # Log data
        LOGGER.debug("Vehicle Type: %s", self.vehicle_type)
        LOGGER.debug("Vehicle Info: %s", data.get("info"))
        LOGGER.debug("Vehicle Status: %s", data.get("status"))
        LOGGER.debug("Vehicle Charging Data: %s", data.get("charging"))
        LOGGER.debug(
            f"State updated: Is Powered On: {self.is_powered_on}, Is Charging: {self.is_charging}, "
            f"Last Powered On Time: {self.last_powered_on_time}, "
            f"Last Powered Off Time: {self.last_powered_off_time}, "
            f"Last Vehicle Activity: {self.last_vehicle_activity}, "
            f"Update Interval: {self.update_interval}"
        )

        # Set the last update time
        self.last_update_time = datetime.now(timezone.utc)

        # Include capabilities in the returned data
        data["capabilities"] = {
            "has_sunroof": self.has_sunroof,
            "has_heated_seats": self.has_heated_seats,
            "has_battery_heating": self.has_battery_heating,
        }

        return data

    # Update Vehicle State
    def _update_state(self, data):
        """Update state variables based on fetched data."""
        status_data = data.get("status")
        charging_data = data.get("charging")
        recent_activity = False

        # Vehicle status
        if status_data:
            basic_status = getattr(status_data, "basicVehicleStatus", None)
            if basic_status is None:
                LOGGER.warning("basicVehicleStatus is not available in Status Data.")
                return

            power_mode = getattr(basic_status, "powerMode", None)

            # Detect Power State
            # Track previous state so we catch the transition even if a prior
            # poll returned None (generic response during power-down window)
            self._prev_is_powered_on = self.is_powered_on
            if power_mode in [2, 3]:
                if not self.is_powered_on:
                    self.last_powered_on_time = datetime.now(timezone.utc)
                self.is_powered_on = True
            else:
                if self.is_powered_on:
                    self.last_powered_off_time = datetime.now(timezone.utc)
                    LOGGER.info(
                        "Vehicle powered off detected for VIN %s — "
                        "starting post-shutdown refresh sequence",
                        self.vin,
                    )
                    self._start_shutdown_refresh_sequence()
                self.is_powered_on = False

            # Detect vehicle activity
            recent_activity = self._detect_activity(basic_status, charging_data)

        # Charging status
        self.is_charging = False
        if charging_data:
            chrg_mgmt_data = getattr(charging_data, "chrgMgmtData", None)
            if chrg_mgmt_data:
                self.is_charging = (
                    getattr(chrg_mgmt_data, "bmsChrgSts", None) in CHARGING_STATUS_CODES
                )

        # Missed-transition guard: if vehicle status was unavailable (None) but
        # charging data confirms the car is now charging, we know the car must
        # have powered off. Fire the shutdown sequence if we haven't already.
        if (
            not status_data
            and self.is_charging
            and self._prev_is_powered_on
            and self.is_powered_on  # still True because status block was skipped
        ):
            if self._shutdown_refresh_task is None or self._shutdown_refresh_task.done():
                LOGGER.info(
                    "Charging detected after status unavailable for VIN %s — "
                    "inferring shutdown, starting post-shutdown refresh sequence",
                    self.vin,
                )
                self.last_powered_off_time = datetime.now(timezone.utc)
                self.is_powered_on = False
                self._start_shutdown_refresh_sequence()

        # Update activity timestamp
        if recent_activity:
            new_activity_time = datetime.now(timezone.utc)
            if self.last_vehicle_activity != new_activity_time:
                self.last_vehicle_activity = new_activity_time
                LOGGER.debug(
                    "Updated Last Vehicle Activity: %s", self.last_vehicle_activity
                )

        # Notify listeners of data changes
        self.async_update_listeners()

    # Chech Vehicle Activity
    def _detect_activity(self, basic_status, charging_data=None):
        """Detect recent activity based on changes in vehicle status and charging."""
        activity_keys = [
            "lockStatus",
            "driverDoor",
            "passengerDoor",
            "rearLeftDoor",
            "rearRightDoor",
            "bootStatus",
            "bonnetStatus",
            "remoteClimateStatus",
            "rmtHtdRrWndSt",
            "engineStatus",
        ]
        detected_activity = False

        # Check for door, lock, and other physical activity
        for key in activity_keys:
            current_value = getattr(basic_status, key, None)
            last_value = getattr(self, f"_last_{key}", None)
            if current_value != last_value:
                LOGGER.debug(
                    "Detected activity for %s: previous=%s, current=%s",
                    key,
                    last_value,
                    current_value,
                )
                setattr(self, f"_last_{key}", current_value)
                detected_activity = True

        # Check for power state changes
        power_mode = getattr(basic_status, "powerMode", None)
        if power_mode is not None and power_mode != getattr(
            self, "_last_power_mode", None
        ):
            LOGGER.debug(
                "Detected power mode change: previous=%s, current=%s",
                getattr(self, "_last_power_mode", None),
                power_mode,
            )
            self._last_power_mode = power_mode
            detected_activity = True

        # Check for charging status changes
        if charging_data:
            charging_status = getattr(charging_data, "bmsChrgSts", None)
            if charging_status != getattr(self, "_last_charging_status", None):
                LOGGER.debug(
                    "Detected charging status change: previous=%s, current=%s",
                    getattr(self, "_last_charging_status", None),
                    charging_status,
                )
                self._last_charging_status = charging_status
                detected_activity = True

        # Log no activity detected
        if not detected_activity:
            LOGGER.debug("No changes detected in monitored keys or charging status.")

        return detected_activity

    # Adjust Update Intervals
    def _adjust_update_interval(self):
        """Adjust update interval dynamically based on state."""
        if getattr(self, "_action_interval_active", False):
            # If we're in an action interval sequence, do not override intervals.
            LOGGER.debug(
                "Action interval active, skipping dynamic interval adjustment."
            )
            return

        now = datetime.now(timezone.utc)

        # Use restored or initialized timestamps for calculations
        last_powered_off_time = self.last_powered_off_time or (
            now - timedelta(hours=24)
        )
        last_vehicle_activity = self.last_vehicle_activity or (
            now - timedelta(hours=24)
        )

        # Calculate durations since last activity or powered-off state
        idle_duration = now - last_powered_off_time
        activity_duration = now - last_vehicle_activity

        LOGGER.debug(
            "Evaluating interval adjustment: Powered On: %s, Charging: %s, "
            "Idle Duration: %s, Activity Duration: %s",
            self.is_powered_on,
            self.is_charging,
            idle_duration,
            activity_duration,
        )

        # Determine update interval based on state and recent activity
        self.update_interval = select_update_interval(
            is_powered_on=self.is_powered_on,
            is_charging=self.is_charging,
            idle_duration=idle_duration,
            activity_duration=activity_duration,
            default_update_interval=self.default_update_interval,
            powered_update_interval=self.powered_update_interval,
            charging_update_interval=self.charging_update_interval,
            grace_period_update_interval=self.grace_period_update_interval,
            after_shutdown_update_interval=self.after_shutdown_update_interval,
        )

        if self.is_powered_on:
            LOGGER.debug("Vehicle is powered on. Using powered update interval.")
        elif self.is_charging:
            LOGGER.debug("Vehicle is charging. Using charging update interval.")
        elif self.update_interval == self.grace_period_update_interval:
            LOGGER.debug("Within grace period. Using grace period interval.")
        elif self.update_interval == self.after_shutdown_update_interval:
            LOGGER.debug("Within shutdown window. Using shutdown interval.")
        else:
            LOGGER.debug("No recent activity. Using default update interval.")

        # Log and schedule the next refresh
        LOGGER.debug(f"Adjusted update interval: {self.update_interval}.")
        self._schedule_refresh()

    # Additional Update Intervals for Actions and Confirmation
    async def schedule_action_refresh(self, vin, immediate_interval, long_interval):
        """Schedule non-blocking follow-up refreshes after an action."""
        self._action_refresh_generation += 1
        generation = self._action_refresh_generation

        if self._action_refresh_task and not self._action_refresh_task.done():
            self._action_refresh_task.cancel()

        self._action_refresh_task = self.hass.async_create_task(
            self._run_action_refresh_sequence(
                vin,
                immediate_interval,
                long_interval,
                generation,
            )
        )

    async def _run_action_refresh_sequence(
        self,
        vin,
        immediate_interval,
        long_interval,
        generation,
    ):
        """Run action follow-up refreshes in the background."""
        self._action_interval_active = True

        try:
            self.update_interval = immediate_interval
            self.next_update_time = utcnow() + self.update_interval
            self.async_update_listeners()
            LOGGER.debug(
                "Scheduling immediate refresh with interval %s for VIN: %s.",
                immediate_interval,
                vin,
            )
            await self.async_request_refresh()

            await asyncio.sleep(immediate_interval.total_seconds())

            self.update_interval = long_interval
            self.next_update_time = utcnow() + self.update_interval
            self.async_update_listeners()
            LOGGER.debug(
                "Switching to long interval %s for VIN: %s after immediate refresh.",
                long_interval,
                vin,
            )
            await self.async_request_refresh()

            await asyncio.sleep(long_interval.total_seconds())
        except asyncio.CancelledError:
            LOGGER.debug("Cancelled action refresh sequence for VIN: %s.", vin)
            raise
        finally:
            if generation == self._action_refresh_generation:
                self._action_interval_active = False
                self._action_refresh_task = None
                self._adjust_update_interval()


    # ── Post-shutdown rapid refresh sequence ─────────────────────────────────

    def _start_shutdown_refresh_sequence(self) -> None:
        """Kick off a background task that polls rapidly after engine-off.

        Because the SAIC REST API has no dedicated shutdown alarm type, the
        coordinator may not poll again for up to 15 minutes after the car
        turns off (it was on the powered-on interval). This sequence fires
        a series of extra refreshes at POST_SHUTDOWN_REFRESH_SEQUENCE intervals
        so that plug-in events are detected within ~1-5 minutes.
        """
        # Cancel any existing shutdown refresh from a previous cycle
        if self._shutdown_refresh_task and not self._shutdown_refresh_task.done():
            self._shutdown_refresh_task.cancel()

        self._shutdown_refresh_task = self.config_entry.async_create_background_task(
            self.hass,
            self._run_shutdown_refresh_sequence(),
            f"mg_saic_shutdown_refresh_{self.vin}",
        )

    async def _run_shutdown_refresh_sequence(self) -> None:
        """Run the post-shutdown refresh sequence."""
        try:
            for delay in POST_SHUTDOWN_REFRESH_SEQUENCE:
                await asyncio.sleep(delay)
                LOGGER.info(
                    "Post-shutdown refresh for VIN %s (delay was %ds)",
                    self.vin,
                    delay,
                )
                await self.async_request_refresh()
                # If the car is now charging, the coordinator interval will have
                # already switched to charging interval — we can stop early.
                if self.is_charging:
                    LOGGER.info(
                        "Charging detected for VIN %s — ending post-shutdown sequence",
                        self.vin,
                    )
                    break
        except asyncio.CancelledError:
            LOGGER.debug(
                "Post-shutdown refresh sequence cancelled for VIN %s", self.vin
            )
            raise
        finally:
            self._shutdown_refresh_task = None

    # ── Message queue polling (event-driven updates) ─────────────────────────

    async def _start_message_polling(self) -> None:
        """Start the background task that polls the SAIC alarm message queue."""
        if self._message_poll_task and not self._message_poll_task.done():
            LOGGER.debug("Message poll task already running for VIN %s", self.vin)
            return
        LOGGER.debug(
            "Starting message poll loop for VIN %s (interval: %ds)",
            self.vin,
            MESSAGE_POLL_INTERVAL_SECONDS,
        )
        self._message_poll_task = self.config_entry.async_create_background_task(
            self.hass,
            self._message_poll_loop(),
            f"mg_saic_message_poll_{self.vin}",
        )

    async def _stop_message_polling(self) -> None:
        """Stop the background message poll task."""
        if self._message_poll_task and not self._message_poll_task.done():
            LOGGER.debug("Stopping message poll task for VIN %s", self.vin)
            self._message_poll_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._message_poll_task
        self._message_poll_task = None

    async def _message_poll_loop(self) -> None:
        """Poll the SAIC alarm message queue periodically and react to events."""
        # Initial delay so startup does not pile on to the first coordinator refresh
        await asyncio.sleep(MESSAGE_POLL_INTERVAL_SECONDS)
        while True:
            try:
                await self._check_alarm_messages()
            except asyncio.CancelledError:
                LOGGER.debug("Message poll loop cancelled for VIN %s", self.vin)
                raise
            except Exception as e:
                LOGGER.warning(
                    "Message poll loop error for VIN %s: %s", self.vin, e
                )
            await asyncio.sleep(MESSAGE_POLL_INTERVAL_SECONDS)

    async def _check_alarm_messages(self) -> None:
        """Check the SAIC alarm message queue and force a refresh on key events.

        Paginates through the message queue (page_size=1, like the MQTT gateway)
        until we reach a message we have already seen, collecting all new messages.
        Triggers an immediate coordinator refresh when significant vehicle events
        are detected:
        - Engine start (messageType 323) → refresh to capture driving state
        - Vehicle shutdown (offCar) → refresh to capture final parked state
        - Charging started (plug-in) → refresh to update charging state
        """
        all_new_messages = []
        page = 1
        max_pages = 20  # Safety limit

        while page <= max_pages:
            try:
                response = await self.client.get_alarm_messages(
                    page_num=page, page_size=1
                )
            except Exception as e:
                LOGGER.warning(
                    "Failed to fetch alarm messages (page %d) for VIN %s: %s",
                    page, self.vin, e,
                )
                break

            if response is None or not getattr(response, "messages", None):
                break

            msg = response.messages[0]

            # Skip messages for other VINs
            if msg.vin and msg.vin != self.vin:
                page += 1
                continue

            # Stop when we reach a message we have already seen
            if msg.messageId is not None and msg.messageId == self._last_seen_message_id:
                break

            # Stop when we reach a message older than our last seen timestamp
            if (
                self._last_seen_message_ts is not None
                and msg.message_time is not None
                and msg.message_time <= self._last_seen_message_ts
            ):
                break

            all_new_messages.append(msg)
            page += 1

        if not all_new_messages:
            LOGGER.debug("No new alarm messages since last check for VIN %s", self.vin)
            return

        # On first run, just record where we are — do NOT act on historical messages.
        # This prevents a burst of spurious refreshes every time HA restarts.
        if self._last_seen_message_id is None:
            latest = all_new_messages[0]
            self._last_seen_message_id = latest.messageId
            self._last_seen_message_ts = latest.message_time
            LOGGER.debug(
                "First message queue check for VIN %s — recording latest id=%s, "
                "skipping %d historical message(s)",
                self.vin,
                latest.messageId,
                len(all_new_messages),
            )
            return

        LOGGER.info(
            "%d new alarm message(s) detected for VIN %s",
            len(all_new_messages),
            self.vin,
        )

        # Record the latest (newest) message we have now seen
        latest = all_new_messages[0]
        self._last_seen_message_id = latest.messageId
        self._last_seen_message_ts = latest.message_time

        should_force_refresh = False
        refresh_reason = None

        for msg in all_new_messages:
            title = (msg.title or "").lower()
            content_text = (msg.content or "").lower()
            msg_type = msg.messageType or ""

            LOGGER.debug(
                "Alarm message for VIN %s: type=%s id=%s title=%s",
                self.vin,
                msg_type,
                msg.messageId,
                msg.title,
            )

            # Engine start (highest priority — break immediately)
            if msg_type == MESSAGE_TYPE_VEHICLE_START or any(
                kw in title for kw in ["start", "engine on", "ignition on", "power on"]
            ):
                LOGGER.info(
                    "Engine start event for VIN %s (type=%s title='%s')",
                    self.vin,
                    msg_type,
                    msg.title,
                )
                should_force_refresh = True
                refresh_reason = "engine start"
                break

            # Vehicle shutdown / offCar equivalent
            if any(kw in title for kw in SHUTDOWN_TITLE_KEYWORDS) or any(
                kw in content_text for kw in SHUTDOWN_TITLE_KEYWORDS
            ):
                LOGGER.info(
                    "Vehicle shutdown event for VIN %s (title='%s')",
                    self.vin,
                    msg.title,
                )
                should_force_refresh = True
                refresh_reason = "vehicle shutdown"

            # Charging / plug-in event
            if any(kw in title for kw in CHARGING_TITLE_KEYWORDS) or any(
                kw in content_text for kw in CHARGING_TITLE_KEYWORDS
            ):
                LOGGER.info(
                    "Charging/plug-in event for VIN %s (title='%s')",
                    self.vin,
                    msg.title,
                )
                should_force_refresh = True
                refresh_reason = (
                    f"{refresh_reason} + charging"
                    if refresh_reason
                    else "charging detected"
                )

        if should_force_refresh:
            LOGGER.info(
                "Forcing coordinator refresh for VIN %s — reason: %s",
                self.vin,
                refresh_reason,
            )
            await self.async_request_refresh()

    async def async_shutdown(self):
        """Release coordinator resources when the entry is unloaded."""
        # Stop background tasks before anything else
        await self._stop_message_polling()
        if self._shutdown_refresh_task and not self._shutdown_refresh_task.done():
            self._shutdown_refresh_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._shutdown_refresh_task

        self._action_refresh_generation += 1

        if self._action_refresh_task and not self._action_refresh_task.done():
            self._action_refresh_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._action_refresh_task
        self._action_refresh_task = None

        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None

    def _schedule_refresh(self):
        """Schedule the next refresh and update listeners."""
        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None

        if self.update_interval and self.update_interval > timedelta(0):
            self.next_update_time = utcnow() + self.update_interval
            self._unsub_refresh = async_track_point_in_utc_time(
                self.hass, self._handle_refresh_interval, self.next_update_time
            )
            LOGGER.debug(
                "Next update scheduled in %s.",
                self.update_interval,
            )
        else:
            self.next_update_time = None
            LOGGER.debug("Update interval is None or zero; no refresh scheduled.")

    async def _handle_refresh_interval(self, now):
        """Handle a scheduled refresh."""
        self._unsub_refresh = None
        await self.async_refresh()

    async def _fetch_with_retries(self, fetch_func, is_generic_func, data_name):
        """Fetch data with retries and handle generic responses."""
        retries = 0
        while retries < RETRY_LIMIT:
            try:
                data = await fetch_func()
                if data is None:
                    LOGGER.warning("%s returned None.", data_name.capitalize())
                    raise UpdateFailed(f"{data_name.capitalize()} is None.")
                if is_generic_func(data):
                    LOGGER.warning("Generic %s response received.", data_name)
                    raise GenericResponseException(f"Generic {data_name} response.")
                return data
            except (UpdateFailed, GenericResponseException, Exception) as e:
                retries += 1
                delay = RETRY_BACKOFF_FACTOR
                LOGGER.warning(
                    "Error fetching %s: %s. Retrying in %s seconds... (Attempt %d/%d)",
                    data_name,
                    e,
                    delay,
                    retries,
                    RETRY_LIMIT,
                )
                await asyncio.sleep(delay)
        LOGGER.error("Failed to fetch %s after %d retries.", data_name, RETRY_LIMIT)
        return None

    def _is_generic_response_vehicle_info(self, vehicle_info):
        """Check if the vehicle info response is generic (placeholder if needed)."""
        return False  # Vehicle info doesn't have known generic responses

    def _is_generic_response_vehicle_status(self, status):
        """Check if the vehicle status response is generic."""
        try:
            if (
                hasattr(status, "basicVehicleStatus")
                and status.basicVehicleStatus.fuelRange
                == GENERIC_RESPONSE_STATUS_THRESHOLD
                and status.basicVehicleStatus.fuelRangeElec
                == GENERIC_RESPONSE_STATUS_THRESHOLD
                and status.basicVehicleStatus.mileage
                == GENERIC_RESPONSE_STATUS_THRESHOLD
                or status.basicVehicleStatus.mileage
                <= GENERIC_RESPONSE_STATUS_THRESHOLD
                or status.basicVehicleStatus.interiorTemperature
                == GENERIC_RESPONSE_TEMPERATURE
                or status.basicVehicleStatus.exteriorTemperature
                == GENERIC_RESPONSE_TEMPERATURE
                # or status.basicVehicleStatus.exteriorTemperature
                # == GENERIC_RESPONSE_EXTREME_TEMPERATURE
            ):
                LOGGER.debug(
                    "Generic Vehicle Status Data: %s", status.basicVehicleStatus
                )
                return True
            return False
        except Exception as e:
            LOGGER.error("Error. Generic Vehicle Status Data: %s", e)
            raise

    def _is_generic_response_charging(self, charging_info):
        """Check if the charging response is generic."""
        try:
            chrgMgmtData = getattr(charging_info, "chrgMgmtData", None)
            if chrgMgmtData:
                if (
                    chrgMgmtData.bmsPackSOCDsp is not None
                    and chrgMgmtData.bmsPackSOCDsp > GENERIC_RESPONSE_SOC_THRESHOLD
                ):
                    LOGGER.debug("Generic Charging Data: %s", chrgMgmtData)
                    return True
            return False
        except Exception as e:
            LOGGER.error("Error. Generic Charging Data: %s", e)
            raise

    def _determine_vehicle_type(self, vehicle_info):
        """Determine the type of vehicle based on its information."""
        vin_info = next((v for v in vehicle_info if v.vin == self.vin), None)
        is_electric = False
        is_combustion = False
        is_hybrid = False

        if not vin_info:
            LOGGER.error(f"No vehicle info found for VIN: {self.vin}")
            return "ICE"  # Default to ICE if unknown

        try:
            for config in vin_info.vehicleModelConfiguration:
                if config.itemCode == "EV":
                    if config.itemValue == "1":
                        is_electric = True
                    elif config.itemValue == "0":
                        is_combustion = True
                if config.itemCode == "BType":
                    if config.itemValue == "1":
                        is_electric = True
                    elif config.itemValue == "0":
                        is_combustion = True
                if config.itemCode == "ENERGY":
                    if config.itemValue == "1":
                        is_hybrid = True
        except Exception as e:
            LOGGER.error("Error determining vehicle type: %s", e)

        # Additional checks
        if (
            "electric" in vin_info.modelName.lower()
            or "ev" in vin_info.modelName.lower()
        ):
            is_electric = True
            is_combustion = False

        if "electric" in vin_info.series.lower() or "ev" in vin_info.series.lower():
            is_electric = True
            is_combustion = False

        if is_electric and not is_combustion:
            return "BEV"
        if is_electric and is_combustion and is_hybrid:
            return "PHEV"
        if is_hybrid and not is_electric:
            return "HEV"
        if not is_electric and is_combustion:
            return "ICE"

        return "ICE"

    def get_sensor_value(self, sensor_name):
        """Retrieve the value for specific sensors."""
        if sensor_name == "last_powered_on":
            return self.last_powered_on_time
        elif sensor_name == "last_powered_off":
            return self.last_powered_off_time
        elif sensor_name == "last_vehicle_activity":
            return self.last_vehicle_activity
        return None

    # ---- AC Temperature Handling ----
    def get_ac_temperature_idx(self, desired_temp: int) -> int:
        """Calculate the temperature index based on the desired temperature.

        Args:
            desired_temp (int): The desired target temperature in Celsius.

        Returns:
            int: The calculated temperature index.

        """

        # Ensure desired_temp is within bounds
        desired_temp = int(max(self.min_temp, min(self.max_temp, desired_temp)))

        temperature_idx = self.temp_offset + (desired_temp - self.min_temp)
        LOGGER.debug(
            f"Calculated temperature index: {temperature_idx} for desired_temp: {desired_temp}°C"
        )
        return temperature_idx


class GenericResponseException(Exception):
    """Exception raised when a generic response is received."""
