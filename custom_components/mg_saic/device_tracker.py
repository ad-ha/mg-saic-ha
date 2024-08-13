from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.event import async_track_time_interval
from .const import DOMAIN, LOGGER, UPDATE_INTERVAL


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the MG SAIC device tracker."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]

    try:
        if not coordinator.data.get("info") or not coordinator.data.get("status"):
            LOGGER.error("Failed to retrieve vehicle info or status.")
            return

        tracker = SAICMGDeviceTracker(coordinator, entry, "gpsPosition", "GPS Location")
        async_add_entities([tracker], update_before_add=True)

    except Exception as e:
        LOGGER.error("Error setting up MG SAIC device tracker: %s", e)


class SAICMGDeviceTracker(TrackerEntity, RestoreEntity):
    def __init__(self, coordinator, entry, field, name):
        self.coordinator = coordinator
        self._field = field
        self._name = name
        self._latitude = None
        self._longitude = None
        vin_info = coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}_gps"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        """Return the name of the device tracker."""
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

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
        vin_info = self.coordinator.data["info"][0]
        return {
            "identifiers": {(DOMAIN, vin_info.vin)},
            "name": f"{vin_info.brandName} {vin_info.modelName}",
            "manufacturer": f"{vin_info.brandName}",
            "model": f"{vin_info.modelName}",
            "serial_number": f"{vin_info.vin}",
        }

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        return {
            "latitude": f"{self._latitude:.6f}" if self._latitude else None,
            "longitude": f"{self._longitude:.6f}" if self._longitude else None,
        }

    async def async_update(self):
        """Fetch new state data for the tracker."""
        try:
            status = self.coordinator.data["status"]
            gps_position = getattr(status, self._field, None)
            if gps_position and gps_position.wayPoint:
                self._latitude = float(gps_position.wayPoint.position.latitude) / 1e6
                self._longitude = float(gps_position.wayPoint.position.longitude) / 1e6
                LOGGER.debug(
                    "Updated GPS location to %f, %f", self._latitude, self._longitude
                )
            self.async_write_ha_state()
        except Exception as e:
            LOGGER.error("Error updating GPS location: %s", e)

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._latitude = float(
                last_state.attributes.get("latitude", self._latitude)
            )
            self._longitude = float(
                last_state.attributes.get("longitude", self._longitude)
            )

        self.async_on_remove(
            async_track_time_interval(self.hass, self.async_update, UPDATE_INTERVAL)
        )
