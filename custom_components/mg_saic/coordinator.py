# coordinator.py
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed
from .api import SAICMGAPIClient
from .const import LOGGER, RETRY_LIMIT, UPDATE_INTERVAL, UPDATE_INTERVAL_CHARGING


class SAICMGDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the MG SAIC API."""

    def __init__(self, hass, client: SAICMGAPIClient, config_entry):
        """Initialize."""
        self.client = client
        self.config_entry = config_entry

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

        self.vehicle_type = None

        # Pass the update interval to the parent class
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

                if vehicle_info is None:
                    LOGGER.error("Vehicle info returned None")
                if vehicle_status is None:
                    LOGGER.error("Vehicle status returned None")
                if charging_info is None:
                    LOGGER.error("Charging info returned None")

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
                    self.update_interval = self.update_interval_charging
                else:
                    # Vehicle is not charging, use the standard update interval
                    self.update_interval = timedelta(
                        seconds=self.config_entry.options.get(
                            "scan_interval", UPDATE_INTERVAL.total_seconds()
                        )
                    )

                return {
                    "info": vehicle_info,
                    "status": vehicle_status,
                    "charging": charging_info,
                }

            raise UpdateFailed("Generic response received after retries")

        except Exception as e:
            LOGGER.error("Error fetching data: %s", e)
            raise UpdateFailed(f"Error fetching data: {e}")

    def _is_generic_response(self, status):
        """Check if the response is generic."""
        try:
            if (
                hasattr(status, "basicVehicleStatus")
                and status.basicVehicleStatus.fuelRange == 0
                and status.basicVehicleStatus.fuelRangeElec == 0
                and status.basicVehicleStatus.mileage == 0
            ):
                return True
            return False
        except Exception as e:
            LOGGER.error("Error checking for generic response: %s", e)
            return False

    def _determine_vehicle_type(self, vehicle_info):
        """Determine the type of vehicle based on its information."""
        vin_info = vehicle_info[0]  # Get the first VIN info
        is_electric = False
        is_combustion = False
        is_hybrid = False

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

        # Additional checks for "electric" or "EV" in the modelName
        if (
            "electric" in vin_info.modelName.lower()
            or "ev" in vin_info.modelName.lower()
        ):
            is_electric = True
            is_combustion = False  # Prioritize BEV over combustion

        # Check the 'series' field for BEV indicators like 'EV'
        if "electric" in vin_info.series.lower() or "ev" in vin_info.series.lower():
            is_electric = True
            is_combustion = False  # Prioritize BEV over combustion

        # Determine the final vehicle type
        if is_electric and not is_combustion:
            return "BEV"
        if is_electric and is_combustion and is_hybrid:
            return "PHEV"
        if is_hybrid and not is_electric:
            return "HEV"
        if not is_electric and is_combustion:
            return "ICE"

        return "ICE"  # Default to ICE if unsure
