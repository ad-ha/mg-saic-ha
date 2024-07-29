import asyncio
from saic_ismart_client_ng import SaicApi
from saic_ismart_client_ng.model import SaicApiConfiguration
from .const import LOGGER


class SAICMGAPIClient:
    def __init__(self, username, password, country_code, region):
        self.username = username
        self.password = password
        self.country_code = country_code
        self.region = region
        self.token = None
        self.saic_api = None
        self.vin = None

    async def login(self):
        """Authenticate with the API and retrieve a token."""
        config = SaicApiConfiguration(username=self.username, password=self.password)
        self.saic_api = SaicApi(config)

        await self.saic_api.login()
        LOGGER.info("Successfully logged in to MG SAIC API")

    async def get_vehicle_info(self):
        if not self.saic_api:
            await self.login()
        vehicle_list_rest = await self.saic_api.vehicle_list()
        vehicle_info = vehicle_list_rest.vinList
        self.vin = vehicle_info[0].vin if vehicle_info else None
        if not self.vin:
            raise ValueError("VIN not found in vehicle info response")
        return vehicle_info

    async def get_vehicle_status(self):
        if not self.vin:
            await self.get_vehicle_info()
        status = await self.saic_api.get_vehicle_status(self.vin)
        LOGGER.debug(f"Vehicle Status: {status.__dict__}")
        return status

    async def send_command(self, command):
        if not self.vin:
            await self.get_vehicle_info()
        # Assuming send_command is a valid method in SaicApi
        return await self.saic_api.send_command(self.vin, command)

    async def start_hvac(self):
        """Start the HVAC system."""
        await self.send_command("start_hvac")

    async def stop_hvac(self):
        """Stop the HVAC system."""
        await self.send_command("stop_hvac")
