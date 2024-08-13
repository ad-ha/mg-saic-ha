import asyncio
from saic_ismart_client_ng import SaicApi
from saic_ismart_client_ng.model import SaicApiConfiguration
from .const import LOGGER, BASE_URLS


class SAICMGAPIClient:
    def __init__(
        self,
        username,
        password,
        vin=None,
        username_is_email=True,
        region=None,
        country_code=None,
    ):
        self.username = username
        self.password = password
        self.vin = vin
        self.saic_api = None
        self.charging_api = None
        self.saic_api = None
        self.saic_api = None
        self.saic_api = None
        self.username_is_email = username_is_email
        self.region = region
        self.country_code = country_code
        self.base_uri = BASE_URLS.get(region)

    async def login(self):
        """Authenticate with the API."""
        config = SaicApiConfiguration(
            username=self.username,
            password=self.password,
            region=self.region,
            phone_country_code=self.country_code
            if not self.username_is_email
            else None,
            username_is_email=self.username_is_email,
        )
        LOGGER.debug(
            "Logging in with region-based endpoint for region: %s", self.region
        )
        self.saic_api = SaicApi(config)

        try:
            await self.saic_api.login()
            LOGGER.debug("Login successful, initializing vehicle APIs.")
        except Exception as e:
            LOGGER.error("Failed to log in to MG SAIC API: %s", e)
            raise

    async def _ensure_initialized(self):
        """Ensure that the APIs are initialized."""
        if not self.saic_api:
            await self.login()

    async def get_vehicle_info(self):
        """Retrieve vehicle information."""
        await self._ensure_initialized()
        try:
            vehicle_list_resp = await self.saic_api.vehicle_list()
            vehicles = vehicle_list_resp.vinList
            self.vin = vehicles[0].vin if vehicles else None
            return vehicles
        except Exception as e:
            LOGGER.error("Error retrieving vehicle info: %s", e)
            return None

    async def get_vehicle_status(self):
        """Retrieve vehicle status."""
        await self._ensure_initialized()
        try:
            vehicle_status = await self.saic_api.get_vehicle_status(self.vin)
            return vehicle_status
        except Exception as e:
            LOGGER.error("Error retrieving vehicle status: %s", e)
            return None

    async def get_charging_info(self):
        """Retrieve charging information."""
        await self._ensure_initialized()

        try:
            charging_status = await self.saic_api.get_vehicle_charging_management_data(
                self.vin
            )
            return charging_status
        except Exception as e:
            LOGGER.error("Error retrieving charging information: %s", e)
            return None

    # Climate control actions
    async def start_ac(self, vin):
        """Start the vehicle AC."""
        await self._ensure_initialized()
        try:
            await self.saic_api.start_ac(vin)
            LOGGER.info("AC started successfully.")
        except Exception as e:
            LOGGER.error("Error starting AC: %s", e)

    async def stop_ac(self, vin):
        """Stop the vehicle AC."""
        await self._ensure_initialized()
        try:
            await self.saic_api.stop_ac(vin)
            LOGGER.info("AC stopped successfully.")
        except Exception as e:
            LOGGER.error("Error stopping AC: %s", e)

    async def control_rear_window_heat(self, vin, action):
        """Control the rear window heat."""
        await self._ensure_initialized()
        try:
            await self.saic_api.control_rear_window_heat(vin, action)
            LOGGER.info("Rear window heat controlled successfully.")
        except Exception as e:
            LOGGER.error("Error controlling rear window heat: %s", e)

    async def control_heated_seats(self, vin, action):
        """Control the heated seats."""
        await self._ensure_initialized()
        try:
            await self.saic_api.control_heated_seats(vin, action)
            LOGGER.info("Heated seats controlled successfully.")
        except Exception as e:
            LOGGER.error("Error controlling heated seats: %s", e)

    async def start_front_defrost(self, vin):
        """Start the front defrost."""
        await self._ensure_initialized()
        try:
            await self.saic_api.start_front_defrost(vin)
            LOGGER.info("Front defrost started successfully.")
        except Exception as e:
            LOGGER.error("Error starting front defrost: %s", e)

    # Locks control actions
    async def lock_vehicle(self, vin):
        """Lock the vehicle."""
        await self._ensure_initialized()
        try:
            await self.saic_api.lock_vehicle(vin)
            LOGGER.info("Vehicle locked successfully.")
        except Exception as e:
            LOGGER.error("Error locking vehicle: %s", e)

    async def unlock_vehicle(self, vin):
        """Unlock the vehicle."""
        await self._ensure_initialized()
        try:
            await self.saic_api.unlock_vehicle(vin)
            LOGGER.info("Vehicle unlocked successfully.")
        except Exception as e:
            LOGGER.error("Error unlocking vehicle: %s", e)

    async def open_tailgate(self, vin):
        """Open the vehicle tailgate."""
        await self._ensure_initialized()
        try:
            await self.saic_api.open_tailgate(vin)
            LOGGER.info("Tailgate opened successfully.")
        except Exception as e:
            LOGGER.error("Error opening tailgate: %s", e)

    # Alarm control actions
    async def trigger_alarm(self, vin):
        """Trigger the vehicle alarm."""
        await self._ensure_initialized()
        try:
            await self.saic_api.set_alarm_switches(vin)
            LOGGER.info("Alarm triggered successfully.")
        except Exception as e:
            LOGGER.error("Error triggering alarm: %s", e)

    async def close(self):
        """Close the client session."""
        try:
            await self.saic_api.close()
            LOGGER.info("Closed MG SAIC API session.")
        except Exception as e:
            LOGGER.error("Error closing MG SAIC API session: %s", e)

    # Charging control actions

    async def send_vehicle_charging_control(self, vin, action):
        """Send a charging control command to the vehicle."""
        await self._ensure_initialized()
        try:
            await self.saic_api.send_vehicle_charging_control(vin, action)
            LOGGER.info(f"Charging {action} command sent successfully for VIN: {vin}")
        except Exception as e:
            LOGGER.error(f"Error sending charging {action} command for VIN {vin}: {e}")
