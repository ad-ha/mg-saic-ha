# coordinator.py

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
    MAX_RETRY_DELAY,
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
        try:
            await self.async_config_entry_first_refresh()
        except Exception as e:
            LOGGER.error("First data update failed: %s", e)
            # Proceed anyway, set data to empty dict
            self.data = {}
        return True

    async def _async_update_data(self):
        """Fetch data from the API."""
        retries = 0
        data = {}
        while retries < RETRY_LIMIT:
            try:
                # Initialize variables to track data validity
                valid_data_fetched = False

                # Fetch charging info
                charging_info = await self.client.get_charging_info()
                if charging_info is None or self._is_generic_charging_response(
                    charging_info
                ):
                    LOGGER.debug("Generic Vehicle Charging Data: %s", charging_info)
                    LOGGER.warning("Charging info is invalid or generic.")
                    charging_info = self.data.get("charging") if self.data else None
                else:
                    data["charging"] = charging_info
                    valid_data_fetched = True

                # Determine charging status
                if charging_info:
                    bms_chrg_sts = getattr(
                        getattr(charging_info, "chrgMgmtData", None), "bmsChrgSts", None
                    )
                    self.is_charging = bms_chrg_sts in CHARGING_STATUS_CODES
                else:
                    self.is_charging = False

                # Fetch vehicle status
                vehicle_status = await self.client.get_vehicle_status()
                if vehicle_status is None or self._is_generic_response(vehicle_status):
                    LOGGER.warning("Vehicle status is invalid or generic.")
                    vehicle_status = self.data.get("status") if self.data else None
                else:
                    data["status"] = vehicle_status
                    valid_data_fetched = True

                # Fetch vehicle info if needed
                fetch_vehicle_info = (
                    self.vehicle_type is None
                    or self.data is None
                    or "info" not in self.data
                    or self.data["info"] is None
                )
                if fetch_vehicle_info:
                    vehicle_info = await self.client.get_vehicle_info()
                    if vehicle_info is None:
                        LOGGER.warning("Vehicle info returned None.")
                        vehicle_info = self.data.get("info") if self.data else None
                    else:
                        data["info"] = vehicle_info
                        valid_data_fetched = True
                else:
                    vehicle_info = self.data.get("info") if self.data else None
                    data["info"] = vehicle_info

                # Log data
                LOGGER.debug("Vehicle Type: %s", self.vehicle_type)
                LOGGER.debug("Vehicle Info: %s", data.get("info"))
                LOGGER.debug("Vehicle Status: %s", data.get("status"))
                LOGGER.debug("Vehicle Charging Data: %s", data.get("charging"))

                # Adjust update interval
                new_interval = (
                    self.update_interval_charging
                    if self.is_charging
                    else self.update_interval
                )
                if self.update_interval != new_interval:
                    self.update_interval = new_interval
                    LOGGER.debug("Update interval set to %s", self.update_interval)
                    if self._unsub_refresh:
                        self._unsub_refresh()
                    self._schedule_refresh()

                # If we have any valid data, return it
                if valid_data_fetched:
                    return data
                else:
                    LOGGER.warning(
                        "No valid data fetched, using previous data if available."
                    )
                    if self.data:
                        return self.data
                    else:
                        return {}

            except Exception as e:
                LOGGER.error("Error fetching data: %s", e)
                retries += 1
                delay = min(retries * RETRY_BACKOFF_FACTOR, MAX_RETRY_DELAY)
                LOGGER.info("Retrying in %s seconds...", delay)
                await asyncio.sleep(delay)

        # After retries exhausted
        LOGGER.error("Failed to fetch data after retries.")
        if self.data:
            LOGGER.info("Using previous data.")
            return self.data
        else:
            LOGGER.error("No previous data available. Returning empty data.")
            return {}

    def _is_generic_response(self, status):
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
                return True
            return False
        except Exception as e:
            LOGGER.error("Error checking for generic response: %s", e)
            return False

    def _is_generic_charging_response(self, charging_info):
        """Check if the charging response is generic."""
        try:
            chrgMgmtData = getattr(charging_info, "chrgMgmtData", None)
            if chrgMgmtData:
                if (
                    chrgMgmtData.bmsPackSOCDsp is not None
                    and chrgMgmtData.bmsPackSOCDsp > GENERIC_RESPONSE_SOC_THRESHOLD
                ):
                    LOGGER.debug("Generic Chargind Data response.")
                    return True
            return False
        except Exception as e:
            LOGGER.error("Error checking for generic charging response: %s", e)
            return False

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
