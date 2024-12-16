from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
import voluptuous as vol
import asyncio

from .api import SAICMGAPIClient
from .const import DOMAIN, LOGGER

SERVICE_CONTROL_CHARGING_PORT_LOCK = "control_charging_port_lock"
SERVICE_CONTROL_HEATED_SEATS = "control_heated_seats"
SERVICE_CONTROL_REAR_WINDOW_HEAT = "control_rear_window_heat"
SERVICE_CONTROL_SUNROOF = "control_sunroof"
SERVICE_LOCK_VEHICLE = "lock_vehicle"
SERVICE_UNLOCK_VEHICLE = "unlock_vehicle"
SERVICE_START_AC = "start_ac"
SERVICE_STOP_AC = "stop_ac"
SERVICE_OPEN_TAILGATE = "open_tailgate"
SERVICE_SET_TARGET_SOC = "set_target_soc"
SERVICE_SET_CHARGE_LIMIT = "set_charge_limit"
SERVICE_START_AC_WITH_SETTINGS = "start_ac_with_settings"
SERVICE_START_BATTERY_HEATING = "start_battery_heating"
SERVICE_START_CHARGING = "start_charging"
SERVICE_START_FRONT_DEFROST = "start_front_defrost"
SERVICE_STOP_BATTERY_HEATING = "stop_battery_heating"
SERVICE_STOP_CHARGING = "stop_charging"
SERVICE_TRIGGER_ALARM = "trigger_alarm"
SERVICE_UPDATE_VEHICLE_DATA = "update_vehicle_data"


SERVICE_ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("vin"): cv.string,
        vol.Required("action"): cv.boolean,
    }
)

SERVICE_PORT_LOCK_SCHEMA = vol.Schema(
    {
        vol.Required("vin"): cv.string,
        vol.Required("unlock"): cv.boolean,
    }
)

SERVICE_REAR_WINDOW_DEFROST_ACTION_SCHEMA = vol.Schema(
    {
        vol.Required("vin"): cv.string,
        vol.Required("action"): vol.In(["start", "stop"]),
    }
)

SERVICE_START_AC_WITH_SETTINGS_SCHEMA = vol.Schema(
    {
        vol.Required("vin"): cv.string,
        vol.Required("temperature"): vol.Coerce(float),
        vol.Required("fan_speed"): vol.Coerce(int),
    }
)

SERVICE_SET_TARGET_SOC_SCHEMA = vol.Schema(
    {
        vol.Required("vin"): cv.string,
        vol.Required("target_soc"): vol.In([40, 50, 60, 70, 80, 90, 100]),
    }
)

SERVICE_SUNROOF_SCHEMA = vol.Schema(
    {
        vol.Required("vin"): cv.string,
        vol.Required("should_open"): cv.boolean,
    }
)

SERVICE_VIN_SCHEMA = vol.Schema({vol.Required("vin"): cv.string})


async def async_setup_services(hass: HomeAssistant, client: SAICMGAPIClient) -> None:
    """Set up services for the MG SAIC integration."""

    async def schedule_data_refresh(vin: str):
        """Schedule a data refresh for the coordinator associated with the VIN."""
        coordinators_by_vin = hass.data[DOMAIN].get("coordinators_by_vin", {})
        coordinator = coordinators_by_vin.get(vin)
        if coordinator:

            async def delayed_refresh():
                await asyncio.sleep(15)
                await coordinator.async_request_refresh()

            hass.async_create_task(delayed_refresh())
        else:
            LOGGER.warning("Coordinator not found for VIN %s", vin)

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

    async def handle_start_ac_with_settings(call: ServiceCall) -> None:
        """Handle the start_ac_with_settings service call."""
        vin = call.data["vin"]
        temperature = call.data["temperature"]
        fan_speed = call.data["fan_speed"]
        try:
            await client.start_climate(vin, temperature, fan_speed)
            LOGGER.info(
                "AC started with temperature %s°C and fan speed %s for VIN: %s",
                temperature,
                fan_speed,
                vin,
            )
            await schedule_data_refresh(vin)
        except Exception as e:
            LOGGER.error("Error starting AC with settings for VIN %s: %s", vin, e)

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

    async def handle_start_battery_heating(call: ServiceCall) -> None:
        """Handle the start_battery_heating service call."""
        vin = call.data["vin"]
        try:
            LOGGER.debug(f"Sending start battery heating command for VIN: {vin}")
            await client.send_vehicle_charging_ptc_heat(vin, "start")
            LOGGER.info(f"Battery heating started successfully for VIN: {vin}")
        except Exception as e:
            LOGGER.error(f"Error starting battery heating for VIN {vin}: {e}")

    async def handle_stop_battery_heating(call: ServiceCall) -> None:
        """Handle the stop_battery_heating service call."""
        vin = call.data["vin"]
        try:
            LOGGER.debug(f"Sending stop battery heating command for VIN: {vin}")
            await client.send_vehicle_charging_ptc_heat(vin, "stop")
            LOGGER.info(f"Battery heating stopped successfully for VIN: {vin}")
        except Exception as e:
            LOGGER.error(f"Error stopping battery heating for VIN {vin}: {e}")

    async def handle_set_target_soc(call: ServiceCall) -> None:
        """Handle the set_target_soc service call."""
        vin = call.data["vin"]
        target_soc = call.data["target_soc"]
        try:
            await client.set_target_soc(vin, target_soc)
        except Exception as e:
            LOGGER.error("Error setting target SOC for VIN %s: %s", vin, e)

    async def handle_set_charge_limit(call: ServiceCall) -> None:
        """Handle the set_charge_limit service call."""
        vin = call.data["vin"]
        target_soc = call.data["target_soc"]
        charge_limit = call.data["charge_limit"]
        try:
            await client.set_charge_limit(vin, charge_limit, target_soc)
        except Exception as e:
            LOGGER.error("Error setting charge limit for VIN %s: %s", vin, e)

    async def handle_control_rear_window_heat(call: ServiceCall) -> None:
        """Handle the control_rear_window_heat service call."""
        vin = call.data["vin"]
        action = call.data["action"]
        try:
            await client.control_rear_window_heat(vin, action)
            LOGGER.info("Rear window heat %sed for VIN: %s", action, vin)
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

    async def handle_update_vehicle_data(call: ServiceCall) -> None:
        """Handle the update_vehicle_data service call."""
        vin = call.data["vin"]
        coordinators_by_vin = hass.data[DOMAIN].get("coordinators_by_vin", {})
        coordinator = coordinators_by_vin.get(vin)
        if coordinator:
            await coordinator.async_request_refresh()
            LOGGER.info("Data update triggered for VIN: %s", vin)
        else:
            LOGGER.warning("Coordinator not found for VIN %s", vin)

    async def handle_control_sunroof(call: ServiceCall) -> None:
        vin = call.data["vin"]
        should_open = call.data["should_open"]
        try:
            await client.control_sunroof(vin, should_open)
            LOGGER.info("Sunroof control action completed for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error controlling sunroof for VIN %s: %s", vin, e)

    async def handle_control_charging_port_lock(call: ServiceCall) -> None:
        vin = call.data["vin"]
        unlock = call.data["unlock"]
        try:
            await client.control_charging_port_lock(vin, unlock)
            LOGGER.info("Charging port lock control action completed for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error controlling charging port lock for VIN %s: %s", vin, e)

    # Register services
    hass.services.async_register(
        DOMAIN,
        SERVICE_CONTROL_CHARGING_PORT_LOCK,
        handle_control_charging_port_lock,
        schema=SERVICE_PORT_LOCK_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CONTROL_HEATED_SEATS,
        handle_control_heated_seats,
        schema=SERVICE_ACTION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CONTROL_REAR_WINDOW_HEAT,
        handle_control_rear_window_heat,
        schema=SERVICE_REAR_WINDOW_DEFROST_ACTION_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CONTROL_SUNROOF,
        handle_control_sunroof,
        schema=SERVICE_SUNROOF_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_LOCK_VEHICLE, handle_lock_vehicle, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_OPEN_TAILGATE, handle_open_tailgate, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TARGET_SOC,
        handle_set_target_soc,
        schema=SERVICE_SET_TARGET_SOC_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_START_AC, handle_start_ac, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_AC_WITH_SETTINGS,
        handle_start_ac_with_settings,
        schema=SERVICE_START_AC_WITH_SETTINGS_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_BATTERY_HEATING,
        handle_start_battery_heating,
        schema=SERVICE_VIN_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_START_CHARGING, handle_start_charging, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_START_FRONT_DEFROST,
        handle_start_front_defrost,
        schema=SERVICE_VIN_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_AC, handle_stop_ac, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_STOP_BATTERY_HEATING,
        handle_stop_battery_heating,
        schema=SERVICE_VIN_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_STOP_CHARGING, handle_stop_charging, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_TRIGGER_ALARM, handle_trigger_alarm, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_UNLOCK_VEHICLE, handle_unlock_vehicle, schema=SERVICE_VIN_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_VEHICLE_DATA,
        handle_update_vehicle_data,
        schema=SERVICE_VIN_SCHEMA,
    )

    LOGGER.info("Services registered for MG SAIC integration.")


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload MG SAIC services."""
    hass.services.async_remove(DOMAIN, SERVICE_CONTROL_CHARGING_PORT_LOCK)
    hass.services.async_remove(DOMAIN, SERVICE_CONTROL_HEATED_SEATS)
    hass.services.async_remove(DOMAIN, SERVICE_CONTROL_REAR_WINDOW_HEAT)
    hass.services.async_remove(DOMAIN, SERVICE_CONTROL_SUNROOF)
    hass.services.async_remove(DOMAIN, SERVICE_LOCK_VEHICLE)
    hass.services.async_remove(DOMAIN, SERVICE_OPEN_TAILGATE)
    hass.services.async_remove(DOMAIN, SERVICE_SET_TARGET_SOC)
    hass.services.async_remove(DOMAIN, SERVICE_START_AC)
    hass.services.async_remove(DOMAIN, SERVICE_START_AC_WITH_SETTINGS)
    hass.services.async_remove(DOMAIN, SERVICE_START_BATTERY_HEATING)
    hass.services.async_remove(DOMAIN, SERVICE_START_CHARGING)
    hass.services.async_remove(DOMAIN, SERVICE_START_FRONT_DEFROST)
    hass.services.async_remove(DOMAIN, SERVICE_STOP_AC)
    hass.services.async_remove(DOMAIN, SERVICE_STOP_BATTERY_HEATING)
    hass.services.async_remove(DOMAIN, SERVICE_STOP_CHARGING)
    hass.services.async_remove(DOMAIN, SERVICE_TRIGGER_ALARM)
    hass.services.async_remove(DOMAIN, SERVICE_UNLOCK_VEHICLE)
    hass.services.async_remove(DOMAIN, SERVICE_UPDATE_VEHICLE_DATA)

    LOGGER.info("Services unregistered for MG SAIC integration.")
