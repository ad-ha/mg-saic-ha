from datetime import timedelta
import asyncio
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import SAICMGAPIClient
from .const import (
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
        await self.async_config_entry_first_refresh()
        return True

    async def _async_update_data(self):
        """Fetch data from the API."""
        retries = 0
        data = {}
        while retries < RETRY_LIMIT:
            try:
                # Fetch charging info to determine charging status
                charging_info = await self.client.get_charging_info()
                if charging_info is None:
                    LOGGER.error("Charging info returned None")
                    raise UpdateFailed("Charging info is None")

                if self._is_generic_charging_response(charging_info):
                    LOGGER.warning("Charging info is generic, retrying...")
                    raise GenericResponseException("Charging info is generic")

                data["charging"] = charging_info

                # Determine if the vehicle is charging
                bms_chrg_sts = getattr(
                    getattr(charging_info, "chrgMgmtData", None), "bmsChrgSts", None
                )
                current_is_charging = bms_chrg_sts in CHARGING_STATUS_CODES

                # Check for charging state change
                charging_state_changed = current_is_charging != self.is_charging

                # Update charging status
                self.is_charging = current_is_charging

                # Determine if it's the first run
                is_first_run = self.data is None or not self.data

                # Fetch Vehicle Info if needed
                fetch_vehicle_info = (
                    charging_state_changed
                    or self.vehicle_type is None
                    or is_first_run
                    or "info" not in self.data
                    or self.data["info"] is None
                )

                # Always fetch Vehicle Status
                vehicle_status = await self.client.get_vehicle_status()
                if vehicle_status is None:
                    LOGGER.error("Vehicle status returned None")
                    raise UpdateFailed("Vehicle status is None")

                if self._is_generic_response(vehicle_status):
                    LOGGER.warning("Vehicle status is generic, retrying...")
                    raise GenericResponseException("Vehicle status is generic")

                # Vehicle status is valid
                data["status"] = vehicle_status

                if fetch_vehicle_info:
                    # Fetch vehicle info
                    vehicle_info = await self.client.get_vehicle_info()
                    if vehicle_info is None:
                        LOGGER.error("Vehicle info returned None")
                        raise UpdateFailed("Vehicle info is None")
                    data["info"] = vehicle_info

                else:
                    data["info"] = self.data.get("info") if self.data else None

                LOGGER.debug("Vehicle Type: %s", self.vehicle_type)
                LOGGER.debug("Vehicle Info: %s", data.get("info"))
                LOGGER.debug("Vehicle Status: %s", data.get("status"))
                LOGGER.debug("Vehicle Charging Data: %s", charging_info)

                # Adjust update interval based on charging status
                new_interval = (
                    self.update_interval_charging
                    if self.is_charging
                    else self.update_interval
                )

                if self.update_interval != new_interval:
                    self.update_interval = new_interval
                    LOGGER.debug("Update interval set to %s", self.update_interval)
                    # Reschedule the updates with the new interval
                    if self._unsub_refresh:
                        self._unsub_refresh()
                    self._schedule_refresh()

                return data

            except GenericResponseException as e:
                retries += 1
                delay = min(retries * RETRY_BACKOFF_FACTOR, MAX_RETRY_DELAY)
                LOGGER.warning(
                    "Received generic response (%s). Retrying (%d/%d) in %s seconds...",
                    e,
                    retries,
                    RETRY_LIMIT,
                    delay,
                )
                await asyncio.sleep(delay)
                continue
            except Exception as e:
                LOGGER.error("Error fetching data: %s", e)
                retries += 1
                delay = min(retries * RETRY_BACKOFF_FACTOR, MAX_RETRY_DELAY)
                LOGGER.info("Retrying in %s seconds...", delay)
                await asyncio.sleep(delay)

        # After retries exhausted, attempt to use previous data
        LOGGER.error(
            "Failed to fetch valid data after retries. Using previous data if available."
        )
        if self.data:
            LOGGER.info("Using previous data.")
            return self.data
        else:
            raise UpdateFailed(
                "Failed to fetch data after retries and no previous data available"
            )

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
                    or chrgMgmtData.bmsChrgOtptCrntReq is not None
                    and chrgMgmtData.bmsChrgOtptCrntReq > GENERIC_RESPONSE_SOC_THRESHOLD
                ):
                    LOGGER.debug(
                        "Generic charging response detected due to high values."
                    )
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
