"""Services for the MG SAIC integration."""
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .api import SAICMGAPIClient
from .const import DOMAIN, LOGGER


async def async_setup_services(hass: HomeAssistant, client: SAICMGAPIClient) -> None:
    """Set up services for MG SAIC integration."""

    async def handle_start_hvac(data: dict[str, Any]) -> None:
        """Handle the start_hvac service call."""
        vin = data["vin"]
        try:
            await client.start_ac(vin)
            LOGGER.info("HVAC started successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error starting HVAC for VIN %s: %s", vin, e)

    async def handle_stop_hvac(data: dict[str, Any]) -> None:
        """Handle the stop_hvac service call."""
        vin = data["vin"]
        try:
            await client.stop_ac(vin)
            LOGGER.info("HVAC stopped successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error stopping HVAC for VIN %s: %s", vin, e)

    async def handle_start_charging(data: dict[str, Any]) -> None:
        """Handle the start_charging service call."""
        vin = data["vin"]
        try:
            await client.control_charging("start")
            LOGGER.info("Charging started successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error starting charging for VIN %s: %s", vin, e)

    async def handle_stop_charging(data: dict[str, Any]) -> None:
        """Handle the stop_charging service call."""
        vin = data["vin"]
        try:
            await client.control_charging("stop")
            LOGGER.info("Charging stopped successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error stopping charging for VIN %s: %s", vin, e)

    async def handle_lock_vehicle(data: dict[str, Any]) -> None:
        """Handle the lock_vehicle service call."""
        vin = data["vin"]

        # Add logging to inspect the 'client' object
        LOGGER.debug("Client object in handle_lock_vehicle: %s", client)
        LOGGER.debug("client.saic_api: %s", client.saic_api)
        if hasattr(client.saic_api, "base_uri"):
            LOGGER.debug("client.saic_api.base_uri: %s", client.saic_api.base_uri)
        else:
            LOGGER.error("client.saic_api.base_uri is missing!")

        try:
            await client.lock_vehicle(vin)
            LOGGER.info("Vehicle locked successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error locking vehicle for VIN %s: %s", vin, e)

    async def handle_unlock_vehicle(data: dict[str, Any]) -> None:
        """Handle the unlock_vehicle service call."""
        vin = data["vin"]
        try:
            await client.unlock_vehicle(vin)
            LOGGER.info("Vehicle unlocked successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error unlocking vehicle for VIN %s: %s", vin, e)

    async def handle_open_tailgate(data: dict[str, Any]) -> None:
        """Handle the open_tailgate service call."""
        vin = data["vin"]
        try:
            await client.open_tailgate(vin)
            LOGGER.info("Tailgate opened successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error opening tailgate for VIN %s: %s", vin, e)

    async def handle_trigger_alarm(data: dict[str, Any]) -> None:
        """Handle the trigger_alarm service call."""
        vin = data["vin"]
        try:
            await client.trigger_alarm(vin)
            LOGGER.info("Alarm triggered successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error triggering alarm for VIN %s: %s", vin, e)

    async def handle_control_rear_window_heat(data: dict[str, Any]) -> None:
        """Handle the control_rear_window_heat service call."""
        vin = data["vin"]
        action = data["action"]
        try:
            await client.control_rear_window_heat(vin, action)
            LOGGER.info("Rear window heat controlled successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error controlling rear window heat for VIN %s: %s", vin, e)

    async def handle_control_heated_seats(data: dict[str, Any]) -> None:
        """Handle the control_heated_seats service call."""
        vin = data["vin"]
        action = data["action"]
        try:
            await client.control_heated_seats(vin, action)
            LOGGER.info("Heated seats controlled successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error controlling heated seats for VIN %s: %s", vin, e)

    async def handle_start_front_defrost(data: dict[str, Any]) -> None:
        """Handle the start_front_defrost service call."""
        vin = data["vin"]
        try:
            await client.start_front_defrost(vin)
            LOGGER.info("Front defrost started successfully for VIN: %s", vin)
        except Exception as e:
            LOGGER.error("Error starting front defrost for VIN %s: %s", vin, e)

    # Register actions
    hass.actions.register(
        DOMAIN,
        "start_hvac",
        handle_start_hvac,
        cv.make_entity_service_schema({"vin": cv.string}),
    )
    hass.actions.register(
        DOMAIN,
        "stop_hvac",
        handle_stop_hvac,
        cv.make_entity_service_schema({"vin": cv.string}),
    )
    hass.actions.register(
        DOMAIN,
        "start_charging",
        handle_start_charging,
        cv.make_entity_service_schema({"vin": cv.string}),
    )
    hass.actions.register(
        DOMAIN,
        "stop_charging",
        handle_stop_charging,
        cv.make_entity_service_schema({"vin": cv.string}),
    )
    hass.actions.register(
        DOMAIN,
        "lock_vehicle",
        handle_lock_vehicle,
        cv.make_entity_service_schema({"vin": cv.string}),
    )
    hass.actions.register(
        DOMAIN,
        "unlock_vehicle",
        handle_unlock_vehicle,
        cv.make_entity_service_schema({"vin": cv.string}),
    )
    hass.actions.register(
        DOMAIN,
        "open_tailgate",
        handle_open_tailgate,
        cv.make_entity_service_schema({"vin": cv.string}),
    )
    hass.actions.register(
        DOMAIN,
        "trigger_alarm",
        handle_trigger_alarm,
        cv.make_entity_service_schema({"vin": cv.string}),
    )
    hass.actions.register(
        DOMAIN,
        "control_rear_window_heat",
        handle_control_rear_window_heat,
        cv.make_entity_service_schema(
            {
                "vin": cv.string,
                "action": cv.boolean,
            }
        ),
    )
    hass.actions.register(
        DOMAIN,
        "control_heated_seats",
        handle_control_heated_seats,
        cv.make_entity_service_schema(
            {
                "vin": cv.string,
                "action": cv.boolean,
            }
        ),
    )
    hass.actions.register(
        DOMAIN,
        "start_front_defrost",
        handle_start_front_defrost,
        cv.make_entity_service_schema({"vin": cv.string}),
    )
