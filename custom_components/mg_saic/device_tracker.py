from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, LOGGER


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


class SAICMGDeviceTracker(CoordinatorEntity, TrackerEntity):
    """Representation of a MG SAIC device tracker."""

    def __init__(self, coordinator, entry, field, name):
        super().__init__(coordinator)
        self._field = field
        self._name = name
        vin_info = self.coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}_gps"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def latitude(self):
        status = self.coordinator.data.get("status")
        if status:
            gps_position = getattr(status, self._field, None)
            if (
                gps_position
                and gps_position.wayPoint
                and gps_position.wayPoint.position
            ):
                return gps_position.wayPoint.position.latitude / 1e6
        return None

    @property
    def longitude(self):
        status = self.coordinator.data.get("status")
        if status:
            gps_position = getattr(status, self._field, None)
            if (
                gps_position
                and gps_position.wayPoint
                and gps_position.wayPoint.position
            ):
                return gps_position.wayPoint.position.longitude / 1e6
        return None

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
            "manufacturer": vin_info.brandName,
            "model": vin_info.modelName,
            "serial_number": vin_info.vin,
        }
