# File: __init__.py

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .api import SAICMGAPIClient
from .coordinator import SAICMGDataUpdateCoordinator
from .const import DOMAIN, LOGGER, PLATFORMS
from .services import async_setup_services, async_unload_services


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

        # Fetch vehicle info to get the VIN
        if not vin:
            LOGGER.error("No VIN specified in Config Entry")
            return False

        # Verify the VIN belongs to the account
        vehicles = await client.get_vehicle_info()
        if not any(v.vin == vin for v in vehicles):
            LOGGER.error("VIN %s not found in account vehicles", vin)
            return False

        hass.data[DOMAIN][entry.entry_id] = client

        coordinator = SAICMGDataUpdateCoordinator(hass, client, entry)
        await coordinator.async_setup()

        hass.data[DOMAIN][f"{entry.entry_id}_coordinator"] = coordinator

        # Store coordinator by VIN for data refresh after service calls
        hass.data[DOMAIN].setdefault("coordinators_by_vin", {})
        hass.data[DOMAIN]["coordinators_by_vin"][vin] = coordinator

        # Register an update listener to handle options updates
        entry.async_on_unload(entry.add_update_listener(update_listener))

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        # Register Services
        await async_setup_services(hass, client, coordinator)

        LOGGER.info("MG SAIC integration setup completed successfully.")
        return True
    except Exception as e:
        LOGGER.error("Failed to set up MG SAIC integration: %s", e)
        return False


async def update_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Handle options update."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]
    await coordinator.async_update_options(entry.options)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        # If there are no more entries, unload services
        if not hass.data[DOMAIN]:
            await async_unload_services(hass)

    return unload_ok
