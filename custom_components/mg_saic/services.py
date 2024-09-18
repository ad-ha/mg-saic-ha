"""Services for the MG SAIC integration."""
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .api import SAICMGAPIClient
from .const import DOMAIN, LOGGER

SERVICE_LOCK_VEHICLE = "lock_vehicle"
SERVICE_UNLOCK_VEHICLE = "unlock_vehicle"
SERVICE_START_AC = "start_ac"
SERVICE_STOP_AC = "stop_ac"
SERVICE_OPEN_TAILGATE = "open_tailgate"
SERVICE_TRIGGER_ALARM = "trigger_alarm"
SERVICE_START_CHARGING = "start_charging"
SERVICE_STOP_CHARGING = "stop_charging"
SERVICE_CONTROL_REAR_WINDOW_HEAT = "control_rear_window_heat"
SERVICE_CONTROL_HEATED_SEATS = "control_heated_seats"
SERVICE_START_FRONT_DEFROST = "start_front_defrost"

SERVICE_VIN_SCHEMA = vol.Schema({vol.Required("vin"): cv.string})

SERVICE_ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("vin"): cv.string,
        vol.Required("action"): cv.boolean,
    }
)


async def async_setup_services(hass: HomeAssistant, client: SAICMGAPIClient) -> None:
    """Set up services for the MG SAIC integration."""

    async def handle_lock_vehicle(call: ServiceCall) -> None:
        """Handle the lock_vehicle service call."""
        vin = call.data["vin"]
        try:
            await client.lock_vehicle(vin)
            LOGGER.info("Vehicle locked successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error locking vehicle for VIN %s: %s", vin, e)

    async def handle_unlock_vehicle(call: ServiceCall) -> None:
        """Handle the unlock_vehicle service call."""
        vin = call.data["vin"]
        try:
            await client.unlock_vehicle(vin)
            LOGGER.info("Vehicle unlocked successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error unlocking vehicle for VIN %s: %s", vin, e)

    async def handle_start_ac(call: ServiceCall) -> None:
        """Handle the start_ac service call."""
        vin = call.data["vin"]
        try:
            await client.start_ac(vin)
            LOGGER.info("AC started successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error starting AC for VIN %s: %s", vin, e)

    async def handle_stop_ac(call: ServiceCall) -> None:
        """Handle the stop_ac service call."""
        vin = call.data["vin"]
        try:
            await client.stop_ac(vin)
            LOGGER.info("AC stopped successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error stopping AC for VIN %s: %s", vin, e)

    async def handle_open_tailgate(call: ServiceCall) -> None:
        """Handle the open_tailgate service call."""
        vin = call.data["vin"]
        try:
            await client.open_tailgate(vin)
            LOGGER.info("Tailgate opened successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error opening tailgate for VIN %s: %s", vin, e)

    async def handle_trigger_alarm(call: ServiceCall) -> None:
        """Handle the trigger_alarm service call."""
        vin = call.data["vin"]
        try:
            await client.trigger_alarm(vin)
            LOGGER.info("Alarm triggered successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error triggering alarm for VIN %s: %s", vin, e)

    async def handle_start_charging(call: ServiceCall) -> None:
        """Handle the start_charging service call."""
        vin = call.data["vin"]
        try:
            LOGGER.debug(f"Sending start charging command for VIN: {vin}")
            await client.send_vehicle_charging_control(vin, "start")
            LOGGER.info(f"Charging started successfully for VIN: {vin}")
        except Exception as e:
            LOGGER.error(f"Error starting charging for VIN {vin}: {e}")

    async def handle_stop_charging(call: ServiceCall) -> None:
        """Handle the stop_charging service call."""
        vin = call.data["vin"]
        try:
            LOGGER.debug(f"Sending stop charging command for VIN: {vin}")
            await client.send_vehicle_charging_control(vin, "stop")
            LOGGER.info(f"Charging stopped successfully for VIN: {vin}")
        except Exception as e:
            LOGGER.error(f"Error stopping charging for VIN {vin}: {e}")

    async def handle_control_rear_window_heat(call: ServiceCall) -> None:
        """Handle the control_rear_window_heat service call."""
        vin = call.data["vin"]
        action = call.data["action"]
        try:
            await client.control_rear_window_heat(vin, action)
            LOGGER.info("Rear window heat controlled successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error controlling rear window heat for VIN %s: %s", vin, e)

    async def handle_control_heated_seats(call: ServiceCall) -> None:
        """Handle the control_heated_seats service call."""
        vin = call.data["vin"]
        action = call.data["action"]
        try:
            await client.control_heated_seats(vin, action)
            LOGGER.info("Heated seats controlled successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error controlling heated seats for VIN %s: %s", vin, e)

    async def handle_start_front_defrost(call: ServiceCall) -> None:
        """Handle the start_front_defrost service call."""
        vin = call.data["vin"]
        try:
            await client.start_front_defrost(vin)
            LOGGER.info("Front defrost started successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error starting front defrost for VIN %s: %s", vin, e)

    # Register services
    hass.services.async_register(
        DOMAIN, SERVICE_LOCK_VEHICLE, handle_lock_vehicle, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_UNLOCK_VEHICLE, handle_unlock_vehicle, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_START_AC, handle_start_ac, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_AC, handle_stop_ac, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_OPEN_TAILGATE, handle_open_tailgate, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_TRIGGER_ALARM, handle_trigger_alarm, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_START_CHARGING, handle_start_charging, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_CHARGING, handle_stop_charging, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CONTROL_REAR_WINDOW_HEAT,
        handle_control_rear_window_heat,
        schema=SERVICE_ACTION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CONTROL_HEATED_SEATS,
        handle_control_heated_seats,
        schema=SERVICE_ACTION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_FRONT_DEFROST,
        handle_start_front_defrost,
        schema=SERVICE_VIN_SCHEMA,
    )

    LOGGER.info("Services registered for MG SAIC integration.")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload MG SAIC services."""
    hass.services.async_remove(DOMAIN, SERVICE_LOCK_VEHICLE)
    hass.services.async_remove(DOMAIN, SERVICE_UNLOCK_VEHICLE)
    hass.services.async_remove(DOMAIN, SERVICE_START_AC)
    hass.services.async_remove(DOMAIN, SERVICE_STOP_AC)
    hass.services.async_remove(DOMAIN, SERVICE_OPEN_TAILGATE)
    hass.services.async_remove(DOMAIN, SERVICE_TRIGGER_ALARM)
    hass.services.async_remove(DOMAIN, SERVICE_START_CHARGING)
    hass.services.async_remove(DOMAIN, SERVICE_STOP_CHARGING)
    hass.services.async_remove(DOMAIN, SERVICE_CONTROL_REAR_WINDOW_HEAT)
    hass.services.async_remove(DOMAIN, SERVICE_CONTROL_HEATED_SEATS)
    hass.services.async_remove(DOMAIN, SERVICE_START_FRONT_DEFROST)

    LOGGER.info("Services unregistered for MG SAIC integration.")
