from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service import verify_domain_control
from .api import SAICMGAPIClient
from .coordinator import SAICMGDataUpdateCoordinator
from .const import DOMAIN, LOGGER, PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up MG SAIC from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data["username"]
    password = entry.data["password"]
    vin = entry.data.get("vin")
    region = entry.data.get("region")
    username_is_email = entry.data.get("country_code") is None

    client = SAICMGAPIClient(
        username,
        password,
        vin,
        username_is_email,
        region,
        entry.data.get("country_code"),
    )

    try:
        await client.login()
        hass.data[DOMAIN][entry.entry_id] = client

        coordinator = SAICMGDataUpdateCoordinator(hass, client)
        await coordinator.async_setup()

        hass.data[DOMAIN][f"{entry.entry_id}_coordinator"] = coordinator

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Register Services (Pass the 'client' object)
        _register_services(hass, client)

        LOGGER.info("MG SAIC integration setup completed successfully.")
        return True
    except Exception as e:
        LOGGER.error("Failed to set up MG SAIC integration: %s", e)
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def _register_services(hass: HomeAssistant, client: SAICMGAPIClient):
    """Register custom services for the MG SAIC integration."""

    # Ensure that only this domain can control these services
    verify_domain_control(hass, DOMAIN)

    async def _lock_vehicle_service(call):
        vin = call.data.get("vin")
        await client.lock_vehicle(vin)

    async def _unlock_vehicle_service(call):
        vin = call.data.get("vin")
        await client.unlock_vehicle(vin)

    async def _open_tailgate_service(call):
        vin = call.data.get("vin")
        await client.open_tailgate(vin)

    async def _trigger_alarm_service(call):
        vin = call.data.get("vin")
        await client.trigger_alarm(vin)

    async def _start_ac_service(call):
        vin = call.data.get("vin")
        await client.start_ac(vin)

    async def _stop_ac_service(call):
        vin = call.data.get("vin")
        await client.stop_ac(vin)

    async def _start_charging_service(call):
        vin = call.data.get("vin")
        await client.send_vehicle_charging_control(vin, "start")

    async def _stop_charging_service(call):
        vin = call.data.get("vin")
        await client.send_vehicle_charging_control(vin, "stop")

    async def _control_rear_window_heat_service(call):
        vin = call.data.get("vin")
        action = call.data.get("action")
        await client.control_rear_window_heat(vin, action)

    async def _control_heated_seats_service(call):
        vin = call.data.get("vin")
        action = call.data.get("action")
        await client.control_heated_seats(vin, action)

    async def _start_front_defrost_service(call):
        vin = call.data.get("vin")
        await client.start_front_defrost(vin)

    # Register all services
    hass.services.async_register(DOMAIN, "lock_vehicle", _lock_vehicle_service)
    hass.services.async_register(DOMAIN, "unlock_vehicle", _unlock_vehicle_service)
    hass.services.async_register(DOMAIN, "open_tailgate", _open_tailgate_service)
    hass.services.async_register(DOMAIN, "trigger_alarm", _trigger_alarm_service)
    hass.services.async_register(DOMAIN, "start_ac", _start_ac_service)
    hass.services.async_register(DOMAIN, "stop_ac", _stop_ac_service)
    hass.services.async_register(DOMAIN, "start_charging", _start_charging_service)
    hass.services.async_register(DOMAIN, "stop_charging", _stop_charging_service)
    hass.services.async_register(
        DOMAIN, "control_rear_window_heat", _control_rear_window_heat_service
    )
    hass.services.async_register(
        DOMAIN, "control_heated_seats", _control_heated_seats_service
    )
    hass.services.async_register(
        DOMAIN, "start_front_defrost", _start_front_defrost_service
    )

    LOGGER.info("Services registered for MG SAIC integration.")
