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

        # Store last known good coordinates
        self._last_lat = None
        self._last_lon = None

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
        data = self.coordinator.data.get(self._data_type)
        if data:
            gps_position = getattr(data, self._field, None)
            if gps_position and gps_position.wayPoint:
                lat = gps_position.wayPoint.position.latitude / 1e6
                lon = gps_position.wayPoint.position.longitude / 1e6

                # If the API returns 0,0 coordinates, fallback to last known valid data
                if (lat == 0.0 and lon == 0.0) and (
                    self._last_lat is not None and self._last_lon is not None
                ):
                    return self._last_lat
                else:
                    # Update last known good latitude if not zero
                    if lat != 0.0:
                        self._last_lat = lat
                    return lat
        # Fallback if no new data or data invalid
        return self._last_lat

    @property
    def longitude(self):
        """Return the longitude of the device."""
        data = self.coordinator.data.get(self._data_type)
        if data:
            gps_position = getattr(data, self._field, None)
            if gps_position and gps_position.wayPoint:
                lat = gps_position.wayPoint.position.latitude / 1e6
                lon = gps_position.wayPoint.position.longitude / 1e6

                # If the API returns 0,0 coordinates, fallback to last known valid data
                if (lat == 0.0 and lon == 0.0) and (
                    self._last_lat is not None and self._last_lon is not None
                ):
                    return self._last_lon
                else:
                    # Update last known good longitude if not zero
                    if lon != 0.0:
                        self._last_lon = lon
                    return lon
        # Fallback if no new data or data invalid
        return self._last_lon

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
