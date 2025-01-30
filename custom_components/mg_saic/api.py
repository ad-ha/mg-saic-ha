# File: api.py

import asyncio
from saic_ismart_client_ng import SaicApi
from saic_ismart_client_ng.model import SaicApiConfiguration
from saic_ismart_client_ng.api.vehicle_charging import (
    TargetBatteryCode,
    ChargeCurrentLimitCode as ExternalChargeCurrentLimitCode,
)
from .const import LOGGER, REGION_BASE_URIS, BatterySoc, ChargeCurrentLimitOption


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
        self.username_is_email = username_is_email
        self.country_code = country_code
        self._login_lock = asyncio.Lock()
        if region is None:
            LOGGER.debug("No region specified, defaulting to Europe.")
        self.region_name = region if region is not None else "Europe"

    # GENERAL API HANDLING
    async def _ensure_initialized(self):
        """Ensure that the APIs are initialized and logged in."""
        if not self.saic_api or not self.saic_api.is_logged_in:
            async with self._login_lock:
                if not self.saic_api or not self.saic_api.is_logged_in:
                    await self.login()

    async def _make_api_call(self, api_call, *args, **kwargs):
        """Wrap API calls to handle token expiration and re-login."""
        await self._ensure_initialized()
        try:
            return await api_call(*args, **kwargs)
        except Exception as e:
            error_message = str(e).lower()
            if (
                "invalid session" in error_message
                or "token expired" in error_message
                or "not logged in" in error_message
            ):
                LOGGER.warning(
                    "Token expired or session invalid, attempting to re-login."
                )
                async with self._login_lock:
                    if not self.saic_api.is_logged_in:
                        await self.login()
                try:
                    return await api_call(*args, **kwargs)
                except Exception as retry_e:
                    LOGGER.error(f"API call failed after re-login: {retry_e}")
                    raise
            else:
                LOGGER.error(f"API call failed: {e}")
                raise

    async def login(self):
        """Authenticate with the API."""
        # Get the base_url for this region
        base_uri = REGION_BASE_URIS.get(self.region_name)
        if not base_uri:
            raise ValueError(f"Base URL not defined for region: {self.region_name}")

        config = SaicApiConfiguration(
            username=self.username,
            password=self.password,
            base_uri=base_uri,
            phone_country_code=self.country_code
            if not self.username_is_email
            else None,
            username_is_email=self.username_is_email,
        )
        LOGGER.debug(
            "Logging in with base URL: %s for region: %s", base_uri, self.region_name
        )

        self.saic_api = await asyncio.to_thread(SaicApi, config)

        try:
            await self.saic_api.login()
            if not self.saic_api.is_logged_in:
                raise Exception("Login failed")
            LOGGER.debug("Login successful, initializing vehicle APIs.")
        except Exception as e:
            LOGGER.error("Failed to log in to MG SAIC API: %s", e)
            self.saic_api = None
            raise

    # GET VEHICLE DATA
    async def get_charging_info(self):
        """Retrieve charging information."""
        try:
            charging_status = await self._make_api_call(
                self.saic_api.get_vehicle_charging_management_data, self.vin
            )
            return charging_status
        except Exception as e:
            LOGGER.error("Error retrieving charging information: %s", e)
            return None

    async def get_vehicle_info(self):
        """Retrieve vehicle information."""
        try:
            vehicle_list_resp = await self._make_api_call(self.saic_api.vehicle_list)
            return vehicle_list_resp.vinList
        except Exception as e:
            LOGGER.error("Error retrieving vehicle info: %s", e)
            return None

    async def get_vehicle_status(self):
        """Retrieve vehicle status."""
        try:
            vehicle_status = await self._make_api_call(
                self.saic_api.get_vehicle_status, self.vin
            )
            return vehicle_status
        except Exception as e:
            LOGGER.error("Error retrieving vehicle status: %s", e)
            return None

    # ACTIONS

    # ALARM CONTROL
    async def trigger_alarm(
        self, vin: str, with_horn=True, with_lights=True, should_stop=False
    ):
        """Trigger or stop the alarm (Find My Car feature)."""
        try:
            await self._make_api_call(
                self.saic_api.control_find_my_car,
                vin=vin,
                should_stop=should_stop,
                with_horn=with_horn,
                with_lights=with_lights,
            )
        except Exception as e:
            LOGGER.error(f"Error triggering alarm for VIN {vin}: {e}")
            raise

    # CHARGING CONTROL
    async def send_vehicle_charging_control(self, vin, action):
        """Send a charging control command to the vehicle."""
        try:
            LOGGER.debug(f"Charging control - VIN: {vin}, action: {action}")
            # Use the control_charging method from the saic-python-client-ng library
            if action == "start":
                await self._make_api_call(
                    self.saic_api.control_charging, vin=vin, stop_charging=False
                )
            else:
                await self._make_api_call(
                    self.saic_api.control_charging, vin=vin, stop_charging=True
                )
            LOGGER.info(f"Charging {action} command sent successfully for VIN: {vin}")
        except Exception as e:
            LOGGER.error(f"Error sending charging {action} command for VIN {vin}: {e}")
            raise

    async def send_vehicle_charging_ptc_heat(self, vin, action):
        """Send a battery heating control command to the vehicle."""
        try:
            LOGGER.debug(f"Battery heating control - VIN: {vin}, action: {action}")
            if action == "start":
                await self._make_api_call(
                    self.saic_api.control_battery_heating, vin=vin, enable=True
                )
            else:
                await self._make_api_call(
                    self.saic_api.control_battery_heating, vin=vin, enable=False
                )
            LOGGER.info(
                f"Battery heating {action} command sent successfully for VIN: {vin}"
            )
        except Exception as e:
            LOGGER.error(
                f"Error sending battery heating {action} command for VIN {vin}: {e}"
            )
            raise

    async def set_current_limit(
        self,
        vin: str,
        target_soc: BatterySoc,
        current_limit_code: ChargeCurrentLimitOption,
    ):
        """Set the charging current limit."""
        try:
            LOGGER.debug(
                "Setting charging current limit for VIN %s to %s (%s)",
                vin,
                current_limit_code.limit,
                current_limit_code,
            )

            # Map local enum to external enum
            external_charge_current_limit = self.map_to_external_charge_current_limit(
                current_limit_code
            )

            # Call the API method with the target_soc and new charge_current_limit
            response = await self._make_api_call(
                self.saic_api.set_target_battery_soc,
                vin,
                target_soc,
                external_charge_current_limit,
            )

            LOGGER.info("Charging current limit set successfully: %s", response)
            return response

        except ValueError as e:
            LOGGER.error("Invalid charging current limit: %s", current_limit_code)
            raise
        except Exception as e:
            LOGGER.error("Error setting charging current limit for VIN %s: %s", vin, e)
            raise

    def map_to_external_charge_current_limit(
        self, local_limit: ChargeCurrentLimitOption
    ) -> ExternalChargeCurrentLimitCode:
        """Map local charging current limit to external ChargeCurrentLimitCode."""
        mapping = {
            ChargeCurrentLimitOption.C_IGNORE: ExternalChargeCurrentLimitCode.C_IGNORE,
            ChargeCurrentLimitOption.C_6A: ExternalChargeCurrentLimitCode.C_6A,
            ChargeCurrentLimitOption.C_8A: ExternalChargeCurrentLimitCode.C_8A,
            ChargeCurrentLimitOption.C_16A: ExternalChargeCurrentLimitCode.C_16A,
            ChargeCurrentLimitOption.C_MAX: ExternalChargeCurrentLimitCode.C_MAX,
        }
        external_code = mapping.get(local_limit)
        if external_code is None:
            LOGGER.error(f"Mapping not found for local limit: {local_limit}")
            raise ValueError(f"Mapping not found for local limit: {local_limit}")
        return external_code

    async def set_target_soc(self, vin, target_soc_percentage):
        """Set the target SOC of the vehicle."""
        try:
            # Map percentage to BatterySoc enum
            percentage_to_enum = {
                40: BatterySoc.SOC_40,
                50: BatterySoc.SOC_50,
                60: BatterySoc.SOC_60,
                70: BatterySoc.SOC_70,
                80: BatterySoc.SOC_80,
                90: BatterySoc.SOC_90,
                100: BatterySoc.SOC_100,
            }
            battery_soc = percentage_to_enum.get(target_soc_percentage)
            if battery_soc is None:
                raise ValueError(
                    f"Invalid target SOC percentage: {target_soc_percentage}"
                )
            # Call the method with the enum value
            await self._make_api_call(
                self.saic_api.set_target_battery_soc, vin, battery_soc
            )
            LOGGER.info(
                "Set target SOC to %d%% for VIN: %s", target_soc_percentage, vin
            )
        except Exception as e:
            LOGGER.error("Error setting target SOC for VIN %s: %s", vin, e)
            raise

    # CLIMATE CONTROL
    async def control_heated_seats(self, vin, left_side_level=0, right_side_level=0):
        """Control the heated seats."""
        try:
            # Call the API method with the levels for each side
            await self._make_api_call(
                self.saic_api.control_heated_seats,
                vin=vin,
                left_side_level=left_side_level,
                right_side_level=right_side_level,
            )
            LOGGER.info(
                "Heated seats updated: Left = %d, Right = %d for VIN: %s",
                left_side_level,
                right_side_level,
                vin,
            )
        except Exception as e:
            LOGGER.error("Error controlling heated seats for VIN %s: %s", vin, e)
            raise

    async def control_rear_window_heat(self, vin, action):
        """Control the rear window heat."""
        try:
            if action.lower() == "start":
                enable = True
            elif action.lower() == "stop":
                enable = False
            else:
                raise ValueError(
                    f"Invalid action '{action}'. Expected 'start' or 'stop'."
                )

            await self._make_api_call(
                self.saic_api.control_rear_window_heat, vin, enable=enable
            )
            LOGGER.info("Rear window heat %sed successfully.", action)
        except Exception as e:
            LOGGER.error("Error controlling rear window heat: %s", e)
            raise

    async def start_ac(self, vin, temperature_idx=None):
        """Start the vehicle AC with an optional temperature index."""
        try:
            if temperature_idx is not None:
                if not isinstance(temperature_idx, int):
                    raise TypeError(
                        f"temperature_idx must be int, got {type(temperature_idx)}"
                    )
                await self._make_api_call(
                    self.saic_api.start_ac,
                    vin,
                    temperature_idx=temperature_idx,
                )
                LOGGER.info(
                    f"AC started with temperature index {temperature_idx} for VIN: {vin}."
                )
            else:
                await self._make_api_call(self.saic_api.start_ac, vin)
                LOGGER.info(f"AC started without temperature index for VIN: {vin}.")
        except Exception as e:
            LOGGER.error(f"Error starting AC for VIN {vin}: {e}")
            raise

    async def start_climate(
        self,
        vin: str,
        temperature_idx: int,
        fan_speed: int,
        ac_on: bool,
    ):
        """Start the vehicle AC with temperature and fan speed settings."""
        try:
            # Log the mapping for debugging
            LOGGER.debug(
                f"Climate params - Idx: {temperature_idx}, Fan speed: {fan_speed}, AC On: {ac_on}"
            )

            await self._make_api_call(
                self.saic_api.control_climate,
                vin=vin,
                fan_speed=fan_speed,
                ac_on=ac_on,
                temperature_idx=temperature_idx,
            )
            LOGGER.info(
                "Climate started with AC ON: %s, Temperature index set to %s and fan speed %s for VIN: %s",
                ac_on,
                temperature_idx,
                fan_speed,
                vin,
            )
        except Exception as e:
            LOGGER.error("Error starting AC with settings for VIN %s: %s", vin, e)
            raise

    async def start_front_defrost(self, vin):
        """Start the front defrost."""
        try:
            await self._make_api_call(self.saic_api.start_front_defrost, vin)
            LOGGER.info("Front defrost started successfully.")
        except Exception as e:
            LOGGER.error("Error starting front defrost: %s", e)
            raise

    async def stop_ac(self, vin):
        """Stop the vehicle AC."""
        try:
            await self._make_api_call(self.saic_api.stop_ac, vin)
            LOGGER.info("AC stopped successfully.")
        except Exception as e:
            LOGGER.error("Error stopping AC: %s", e)
            raise

    # LOCKS CONTROL
    async def control_charging_port_lock(self, vin: str, unlock: bool):
        """Control the charging port lock (lock/unlock)."""
        try:
            await self._make_api_call(
                self.saic_api.control_charging_port_lock, vin=vin, unlock=unlock
            )
            LOGGER.info(
                "Charging port %s successfully for VIN: %s",
                "unlocked" if unlock else "locked",
                vin,
            )
        except Exception as e:
            LOGGER.error("Error controlling charging port lock for VIN %s: %s", vin, e)
            raise

    async def lock_vehicle(self, vin):
        """Lock the vehicle."""
        try:
            await self._make_api_call(self.saic_api.lock_vehicle, vin)
            LOGGER.info("Vehicle locked successfully.")
        except Exception as e:
            LOGGER.error("Error locking vehicle: %s", e)

    async def open_tailgate(self, vin):
        """Open the vehicle tailgate."""
        try:
            await self._make_api_call(self.saic_api.open_tailgate, vin)
            LOGGER.info("Tailgate opened successfully.")
        except Exception as e:
            LOGGER.error("Error opening tailgate: %s", e)

    async def unlock_vehicle(self, vin):
        """Unlock the vehicle."""
        try:
            await self._make_api_call(self.saic_api.unlock_vehicle, vin)
            LOGGER.info("Vehicle unlocked successfully.")
        except Exception as e:
            LOGGER.error("Error unlocking vehicle: %s", e)

    # WINDOWS CONTROL
    async def control_sunroof(self, vin, action):
        """Control the sunroof (open/close)."""
        try:
            LOGGER.debug(f"Sunroof control - VIN: {vin}, action: {action}")
            should_open = action == "open"
            await self._make_api_call(
                self.saic_api.control_sunroof, vin=vin, should_open=should_open
            )
            LOGGER.info(f"Sunroof {action} command sent successfully for VIN: {vin}")
        except Exception as e:
            LOGGER.error("Error controlling sunroof for VIN %s: %s", vin, e)
            raise

    # SESSION MANAGEMENT
    async def close(self):
        """Close the client session."""
        try:
            await self.saic_api.close()
            LOGGER.info("Closed MG SAIC API session.")
        except Exception as e:
            LOGGER.error("Error closing MG SAIC API session: %s", e)
