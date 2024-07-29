from homeassistant.components.device_tracker.config_entry import TrackerEntity
from .const import DOMAIN, LOGGER, UPDATE_INTERVAL


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the MG SAIC device tracker."""
    client = hass.data[DOMAIN].get(entry.entry_id)
    if client is None:
        LOGGER.error("Client not initialized")
        return

    try:
        vehicle_status = await client.get_vehicle_status()
    except Exception as e:
        LOGGER.error("Error connecting to MG SAIC API: %s", e)
        return

    tracker = SAICMGDeviceTracker(client, entry)
    async_add_entities([tracker], update_before_add=True)


class SAICMGDeviceTracker(TrackerEntity):
    def __init__(self, client, entry):
        self.client = client
        self._latitude = None
        self._longitude = None
        self._unique_id = f"{entry.entry_id}_{client.vin}_gps"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def latitude(self):
        """Return latitude value of the device."""
        return self._latitude

    @property
    def longitude(self):
        """Return longitude value of the device."""
        return self._longitude

    @property
    def source_type(self):
        """Return the source type of the device."""
        return "gps"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.client.vin)},
            "name": f"MG SAIC {self.client.vin}",
            "manufacturer": "MG SAIC",
        }

    async def async_update(self):
        """Fetch new state data for the tracker."""
        try:
            status = await self.client.get_vehicle_status()
            gps_position = getattr(status, "gpsPosition", None)
            if gps_position and gps_position.wayPoint:
                self._latitude = gps_position.wayPoint.position.latitude / 1e6
                self._longitude = gps_position.wayPoint.position.longitude / 1e6
            self.async_write_ha_state()
        except Exception as e:
            LOGGER.error("Error connecting to MG SAIC API: %s", e)

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.hass.helpers.event.async_track_time_interval(
                self.async_update, UPDATE_INTERVAL
            )
        )
