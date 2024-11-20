from datetime import timedelta
import asyncio
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import SAICMGAPIClient
from .const import (
    DOMAIN,
    LOGGER,
    RETRY_LIMIT,
    UPDATE_INTERVAL,
    UPDATE_INTERVAL_CHARGING,
    RETRY_BACKOFF_FACTOR,
    CHARGING_STATUS_CODES,
    GENERIC_RESPONSE_STATUS_THRESHOLD,
    GENERIC_RESPONSE_SOC_THRESHOLD,
)


class SAICMGDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the MG SAIC API."""

    def __init__(self, hass, client: SAICMGAPIClient, config_entry):
        """Initialize."""
        self.client = client
        self.config_entry = config_entry
        self.is_charging = False
        self.is_initial_setup = False

        # Initialize update intervals from config_entry options, falling back to defaults if not set
        self.update_interval = timedelta(
            seconds=config_entry.options.get(
                "scan_interval", UPDATE_INTERVAL.total_seconds()
            )
        )
        self.update_interval_charging = timedelta(
            seconds=config_entry.options.get(
                "charging_scan_interval", UPDATE_INTERVAL_CHARGING.total_seconds()
            )
        )

        # Use the vehicle type from the config entry
        self.vehicle_type = self.config_entry.data.get("vehicle_type")

        super().__init__(
            hass,
            LOGGER,
            name="MG SAIC data update coordinator",
            update_interval=self.update_interval,
        )

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

        # Determine vehicle type
        self.vehicle_type = self._determine_vehicle_type(data["info"])

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
        if data.get("charging") is not None:
            chrg_data = getattr(data["charging"], "chrgMgmtData", None)
            if chrg_data is not None:
                bms_chrg_sts = getattr(chrg_data, "bmsChrgSts", None)
                self.is_charging = bms_chrg_sts in CHARGING_STATUS_CODES

        # Adjust update interval based on charging status
        new_interval = (
            self.update_interval_charging if self.is_charging else self.update_interval
        )
        if self.update_interval != new_interval:
            self.update_interval = new_interval
            LOGGER.debug("Update interval set to %s", self.update_interval)
            if self._unsub_refresh:
                self._unsub_refresh()
            self._schedule_refresh()

        # Log data
        LOGGER.debug("Vehicle Type: %s", self.vehicle_type)
        LOGGER.debug("Vehicle Info: %s", data.get("info"))
        LOGGER.debug("Vehicle Status: %s", data.get("status"))
        LOGGER.debug("Vehicle Charging Data: %s", data.get("charging"))

        return data

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
