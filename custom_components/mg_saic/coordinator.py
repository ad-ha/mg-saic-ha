# File: coordinator.py

from datetime import datetime, timedelta, timezone
import asyncio
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import utcnow
from .api import SAICMGAPIClient
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
        self.update_interval = get_interval("update_interval", UPDATE_INTERVAL)
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
            f"Default: {self.update_interval}, "
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
        self.update_interval = get_interval("update_interval", UPDATE_INTERVAL)
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
            f"Default: {self.update_interval}, "
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

        # Reschedule the refresh with the new update interval
        if not self.is_charging and not self.is_powered_on:
            new_interval = self.update_interval
            if self.update_interval != new_interval:
                LOGGER.debug(
                    f"Update interval reset to default: {self.update_interval}"
                )
                if self._unsub_refresh:
                    self._unsub_refresh()
                self._schedule_refresh()

        # Reschedule the refresh immediately with the new update interval
        if self._unsub_refresh:
            self._unsub_refresh()

        # Force recalculation of the next update time based on the new interval
        self.next_update_time = utcnow() + self.update_interval
        self._schedule_refresh()

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
            if power_mode in [2, 3]:
                if not self.is_powered_on:
                    self.last_powered_on_time = datetime.now(timezone.utc)
                self.is_powered_on = True
            else:
                if self.is_powered_on:
                    self.last_powered_off_time = datetime.now(timezone.utc)
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
        if self.is_powered_on:
            self.update_interval = self.powered_update_interval
            LOGGER.debug("Vehicle is powered on. Using powered update interval.")
        elif self.is_charging:
            self.update_interval = self.charging_update_interval
            LOGGER.debug("Vehicle is charging. Using charging update interval.")
        elif (
            activity_duration <= self.grace_period_update_interval
            or idle_duration <= self.grace_period_update_interval
        ):
            self.update_interval = self.grace_period_update_interval
            LOGGER.debug("Within grace period. Using grace period interval.")
        elif idle_duration <= self.after_shutdown_update_interval:
            self.update_interval = self.after_shutdown_update_interval
            LOGGER.debug("Within shutdown window. Using shutdown interval.")
        else:
            self.update_interval = UPDATE_INTERVAL  # Use the default update interval
            LOGGER.debug("No recent activity. Using default update interval.")

        # Log and schedule the next refresh
        LOGGER.debug(f"Adjusted update interval: {self.update_interval}.")
        self._schedule_refresh()

    # Additional Update Intervals for Actions and Confirmation
    async def schedule_action_refresh(self, vin, immediate_interval, long_interval):
        """Schedule immediate and long-interval updates after an action."""
        # Prevent state-driven adjustments during action sequence
        self._action_interval_active = True

        try:
            # Apply the immediate interval
            self.update_interval = immediate_interval
            self.next_update_time = utcnow() + self.update_interval
            self.async_update_listeners()
            LOGGER.debug(
                "Scheduling immediate refresh with interval %s for VIN: %s.",
                immediate_interval,
                vin,
            )
            await self.async_request_refresh()

            # Wait for the immediate interval
            await asyncio.sleep(immediate_interval.total_seconds())

            # Apply the long interval
            self.update_interval = long_interval
            self.next_update_time = utcnow() + self.update_interval
            self.async_update_listeners()
            LOGGER.debug(
                "Switching to long interval %s for VIN: %s after immediate refresh.",
                long_interval,
                vin,
            )
            await self.async_request_refresh()

            # Wait for the long interval
            await asyncio.sleep(long_interval.total_seconds())

        finally:
            # Allow state-based adjustments again
            self._action_interval_active = False
            self._adjust_update_interval()

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
