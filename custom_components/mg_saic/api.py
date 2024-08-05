# api.py

from saic_ismart_client_ng import SaicApi
from saic_ismart_client_ng.model import SaicApiConfiguration
from saic_ismart_client_ng.api.vehicle_charging import SaicVehicleChargingApi
from .const import LOGGER


class SAICMGAPIClient:
    def __init__(self, username, password, vin=None):
        self.username = username
        self.password = password
        self.vin = vin
        self.saic_api = None
        self.charging_api = None

    async def login(self):
        """Authenticate with the API."""
        config = SaicApiConfiguration(username=self.username, password=self.password)
        self.saic_api = SaicApi(config)
        await self.saic_api.login()
        LOGGER.info("Successfully logged in to MG SAIC API")
        self.charging_api = SaicVehicleChargingApi(self.saic_api)

    async def get_vehicle_info(self):
        """Retrieve vehicle information."""
        if not self.saic_api:
            await self.login()
        vehicle_list_resp = await self.saic_api.vehicle_list()
        vehicles = vehicle_list_resp.vinList
        self.vin = vehicles[0].vin if vehicles else None
        return vehicles

    async def get_vehicle_status(self):
        """Retrieve vehicle status."""
        if not self.saic_api or not self.vin:
            await self.login()
            await self.get_vehicle_info()
        try:
            vehicle_status = await self.saic_api.get_vehicle_status(self.vin)
            return vehicle_status
        except Exception as e:
            LOGGER.error("Error retrieving vehicle status: %s", e)
            return None

    async def get_charging_info(self):
        """Retrieve charging information."""
        if not self.saic_api or not self.vin:
            await self.login()
            await self.get_vehicle_info()

        try:
            charging_info = await self.charging_api.get_vehicle_charging_status(
                self.vin
            )
            return charging_info
        except Exception as e:
            LOGGER.error("Error retrieving charging information: %s", e)
            return None

    async def control_charging(self, action):
        """Control vehicle charging."""
        if not self.saic_api or not self.vin:
            await self.login()
            await self.get_vehicle_info()

        try:
            await self.charging_api.send_vehicle_charging_control(self.vin, action)
        except Exception as e:
            LOGGER.error("Error controlling charging: %s", e)

    async def close(self):
        """Close the client session."""
        await self.saic_api.close()
