from datetime import datetime, timedelta, timezone
import asyncio
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util.dt import utcnow
from .api import SAICMGAPIClient
from .const import (
    DOMAIN,
    LOGGER,
    RETRY_LIMIT,
    UPDATE_INTERVAL,
    UPDATE_INTERVAL_CHARGING,
    UPDATE_INTERVAL_POWERED,
    RETRY_BACKOFF_FACTOR,
    CHARGING_STATUS_CODES,
    GENERIC_RESPONSE_STATUS_THRESHOLD,
    GENERIC_RESPONSE_SOC_THRESHOLD,
)


class SAICMGDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the MG SAIC API."""

    def __init__(self, hass, client: SAICMGAPIClient, config_entry):
        """Initialize."""
        super().__init__(
            hass,
            LOGGER,
            name="MG SAIC data update coordinator",
            update_interval=None,
        )

        self.client = client
        self.config_entry = config_entry
        self.is_charging = False
        self.is_powered_on = False
        self.is_initial_setup = False

        # Initialize update intervals from config_entry options, falling back to defaults if not set
        self.default_update_interval = timedelta(
            seconds=config_entry.options.get(
                "scan_interval", UPDATE_INTERVAL.total_seconds()
            )
        )
        self.update_interval_charging = timedelta(
            seconds=config_entry.options.get(
                "charging_scan_interval", UPDATE_INTERVAL_CHARGING.total_seconds()
            )
        )
        self.update_interval_powered = timedelta(
            seconds=config_entry.options.get(
                "powered_scan_interval", UPDATE_INTERVAL_POWERED.total_seconds()
            )
        )

        # Start with the default update interval
        self.update_interval = self.default_update_interval

        # Initialize next_update_time
        self.next_update_time = None

        LOGGER.debug(
            f"Update intervals initialized: Default: {self.default_update_interval}, Charging: {self.update_interval_charging}, Powered: {self.update_interval_powered}"
        )

        # Use the vehicle type from the config entry
        self.vehicle_type = self.config_entry.data.get("vehicle_type")

    async def async_update_options(self, options):
        """Update options and reschedule refresh."""
        # Update intervals from options
        self.default_update_interval = timedelta(
            seconds=options.get(
                "scan_interval", self.default_update_interval.total_seconds()
            )
        )
        self.update_interval_charging = timedelta(
            seconds=options.get(
                "charging_scan_interval",
                self.update_interval_charging.total_seconds(),
            )
        )
        self.update_interval_powered = timedelta(
            seconds=options.get(
                "powered_scan_interval",
                self.update_interval_powered.total_seconds(),
            )
        )

        LOGGER.debug(
            f"Update intervals updated via options: Default: {self.default_update_interval}, Charging: {self.update_interval_charging}, Powered: {self.update_interval_powered}"
        )

        # Adjust the update interval if not charging or powered on
        if not self.is_charging and not self.is_powered_on:
            if self.update_interval != self.default_update_interval:
                self.update_interval = self.default_update_interval
                LOGGER.debug(
                    f"Update interval reset to default: {self.update_interval}"
                )
                if self._unsub_refresh:
                    self._unsub_refresh()
                self._schedule_refresh()

    async def async_setup(self):
        """Set up the coordinator."""
        self.is_initial_setup = True
        try:
            await self.async_config_entry_first_refresh()
        except Exception as e:
            LOGGER.error("First data update failed: %s", e)
            # Proceed anyway, set data to empty dict
            self.data = {}
        finally:
            self.is_initial_setup = False
        return True

    async def _async_update_data(self):
        """Fetch data from the API."""
        data = {}

        # Fetch vehicle info with retries
        data["info"] = await self._fetch_with_retries(
            self.client.get_vehicle_info,
            self._is_generic_response_vehicle_info,
            "vehicle info",
        )

        if data["info"] is None:
            # Cannot proceed without vehicle info
            raise UpdateFailed("Cannot proceed without vehicle info.")

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
                LOGGER.debug(
                    f"Charging status code: {bms_chrg_sts}, is_charging: {self.is_charging}"
                )
        else:
            LOGGER.debug("Charging data not available.")

        # Determine if the vehicle is powered on
        self.is_powered_on = False
        status_data = data.get("status")
        if status_data:
            basic_status = getattr(status_data, "basicVehicleStatus", None)
            if basic_status:
                power_mode = getattr(basic_status, "powerMode", None)
                self.is_powered_on = power_mode in [2, 3]
                LOGGER.debug(
                    f"Power mode: {power_mode}, is_powered_on: {self.is_powered_on}"
                )
        else:
            LOGGER.debug("Vehicle status data not available.")

        # Adjust Update Intervals
        if self.is_powered_on:
            new_interval = self.update_interval_powered
        elif self.is_charging:
            new_interval = self.update_interval_charging
        else:
            new_interval = self.default_update_interval

        if self.update_interval != new_interval:
            LOGGER.debug(
                f"Update interval changed from {self.update_interval} to {new_interval}"
            )
            self.update_interval = new_interval
            if self._unsub_refresh:
                self._unsub_refresh()
            self._schedule_refresh()

        # Log data
        LOGGER.debug("Vehicle Type: %s", self.vehicle_type)
        LOGGER.debug("Vehicle Info: %s", data.get("info"))
        LOGGER.debug("Vehicle Status: %s", data.get("status"))
        LOGGER.debug("Vehicle Charging Data: %s", data.get("charging"))

        # Set the last update time
        self.last_update_time = datetime.now(timezone.utc)

        return data

    def _schedule_refresh(self):
        """Schedule a refresh, and update next_update_time."""
        if self._unsub_refresh:
            self._unsub_refresh()
            self._unsub_refresh = None

        if self.update_interval is not None and self.update_interval > timedelta(0):
            self._unsub_refresh = self.hass.helpers.event.async_track_point_in_utc_time(
                self._handle_refresh_interval, utcnow() + self.update_interval
            )
            self.next_update_time = utcnow() + self.update_interval
            LOGGER.debug(f"Next update scheduled at {self.next_update_time}")
        else:
            self.next_update_time = None
            LOGGER.debug("Update interval is None or zero, no next update scheduled.")

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
        vin_info = vehicle_info[0]
        is_electric = False
        is_combustion = False
        is_hybrid = False

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


class GenericResponseException(Exception):
    """Exception raised when a generic response is received."""
