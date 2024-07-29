from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .api import SAICMGAPIClient
from .const import DOMAIN, LOGGER, UPDATE_INTERVAL

PLATFORMS = ["sensor", "binary_sensor", "device_tracker"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up MG SAIC from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    username = entry.data["username"]
    password = entry.data["password"]
    country_code = entry.data.get("country_code")
    region = entry.data["region"]
    vin = entry.data["vin"]

    client = SAICMGAPIClient(username, password, country_code, region)
    await client.login()
    client.vin = vin
    hass.data[DOMAIN][entry.entry_id] = client

    coordinator = SAICMGDataUpdateCoordinator(hass, client)
    await coordinator.async_refresh()

    hass.data[DOMAIN][f"{entry.entry_id}_coordinator"] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class SAICMGDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the MG SAIC API."""

    def __init__(self, hass, client):
        """Initialize."""
        self.client = client
        super().__init__(
            hass,
            LOGGER,
            name="MG SAIC data update coordinator",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            return await self.client.get_vehicle_status()
        except Exception as e:
            raise UpdateFailed(f"Error communicating with API: {e}")
