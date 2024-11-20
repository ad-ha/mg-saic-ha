from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, LOGGER


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the MG SAIC device tracker."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]

    try:
        if not coordinator.data.get("info"):
            LOGGER.error("Failed to retrieve vehicle info or status.")
            return

        tracker = SAICMGDeviceTracker(
            coordinator, entry, "gpsPosition", "GPS Location", data_type="status"
        )
        async_add_entities([tracker], update_before_add=True)

    except Exception as e:
        LOGGER.error("Error setting up MG SAIC device tracker: %s", e)


class SAICMGDeviceTracker(CoordinatorEntity, TrackerEntity):
    """Representation of a MG SAIC device tracker."""

    def __init__(self, coordinator, entry, field, name, data_type):
        super().__init__(coordinator)
        self._field = field
        self._name = name
        self._data_type = data_type
        vin_info = self.coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}_gps"

    @property
    def unique_id(self):
        """Return the unique ID of the tracker."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the tracker."""
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def latitude(self):
        """Return the latitude of the device."""
        try:
            data = self.coordinator.data.get(self._data_type)
            if data:
                gps_position = getattr(data, self._field, None)
                if gps_position and gps_position.wayPoint:
                    return gps_position.wayPoint.position.latitude / 1e6
        except Exception as e:
            LOGGER.error("Error retrieving latitude for %s: %s", self._name, e)
        return None

    @property
    def longitude(self):
        """Return the longitude of the device."""
        try:
            data = self.coordinator.data.get(self._data_type)
            if data:
                gps_position = getattr(data, self._field, None)
                if gps_position and gps_position.wayPoint:
                    return gps_position.wayPoint.position.longitude / 1e6
        except Exception as e:
            LOGGER.error("Error retrieving longitude for %s: %s", self._name, e)
        return None

    @property
    def source_type(self):
        """Return the source type of the device."""
        return "gps"

    @property
    def device_info(self):
        """Return device info for this tracker."""
        vin_info = self.coordinator.data["info"][0]
        return {
            "identifiers": {(DOMAIN, vin_info.vin)},
            "name": f"{vin_info.brandName} {vin_info.modelName}",
            "manufacturer": vin_info.brandName,
            "model": vin_info.modelName,
            "serial_number": vin_info.vin,
        }
