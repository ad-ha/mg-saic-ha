from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
from .api import SAICMGAPIClient
from .const import LOGGER, RETRY_LIMIT, UPDATE_INTERVAL, UPDATE_INTERVAL_CHARGING


class SAICMGDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the MG SAIC API."""

    def __init__(self, hass, client: SAICMGAPIClient):
        """Initialize."""
        self.client = client
        self.vehicle_type = None
        self.update_interval = UPDATE_INTERVAL
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
        try:
            retries = 0
            while retries < RETRY_LIMIT:
                vehicle_info = await self.client.get_vehicle_info()
                vehicle_status = await self.client.get_vehicle_status()
                charging_info = await self.client.get_charging_info()

                # Check for generic response and retry
                if self._is_generic_response(vehicle_status):
                    LOGGER.debug("Discarding generic response, retrying...")
                    retries += 1
                    continue

                # Determine vehicle type
                self.vehicle_type = self._determine_vehicle_type(vehicle_info)

                LOGGER.debug("Fetched data successfully")
                LOGGER.debug("Vehicle Type: %s", self.vehicle_type)
                LOGGER.debug("Vehicle Info: %s", vehicle_info)
                LOGGER.debug("Vehicle Status: %s", vehicle_status)
                LOGGER.debug("Vehicle Charging Data: %s", charging_info)

                # Adjust update interval based on charging status
                if charging_info and charging_info.chrgMgmtData.bmsChrgSts == 1:
                    # Vehicle is charging, reduce the update interval
                    self.update_interval = UPDATE_INTERVAL_CHARGING
                else:
                    # Vehicle is not charging, use the standard update interval
                    self.update_interval = UPDATE_INTERVAL

                return {
                    "info": vehicle_info,
                    "status": vehicle_status,
                    "charging": charging_info,
                }

            raise UpdateFailed("Generic response received after retries")

        except ConfigEntryAuthFailed as auth_err:
            raise ConfigEntryAuthFailed(
                f"Authentication failed: {auth_err}"
            ) from auth_err
        except Exception as e:
            LOGGER.error("Error fetching data: %s", e)
            raise UpdateFailed(f"Error fetching data: {e}")

    def _is_generic_response(self, status):
        """Check if the response is generic."""
        if (
            hasattr(status, "basicVehicleStatus")
            and status.basicVehicleStatus.fuelRange == 0
            and status.basicVehicleStatus.fuelRangeElec == 0
            and status.basicVehicleStatus.mileage == 0
        ):
            return True
        return False

    def _determine_vehicle_type(self, vehicle_info):
        """Determine the type of vehicle based on its information."""
        is_electric = False
        is_combustion = False
        is_hybrid = False

        for config in vehicle_info[0].vehicleModelConfiguration:
            if config.itemCode == "EV" and config.itemValue == "1":
                is_electric = True
            if config.itemCode == "BType":
                if config.itemValue == "1":
                    is_electric = True
                elif config.itemValue == "0":
                    is_hybrid = True
            if config.itemCode == "ENERGY" and config.itemValue == "1":
                is_hybrid = True

        if "electric" in vehicle_info[0].modelName.lower():
            is_electric = True
        if is_electric and not is_combustion:
            return "BEV"
        if is_electric and is_combustion and is_hybrid:
            return "PHEV"
        if not is_electric and is_combustion:
            return "ICE"
        if is_hybrid and not is_electric:
            return "HEV"

        return "ICE"  # Default to ICE if unsure
