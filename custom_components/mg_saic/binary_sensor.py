from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.const import STATE_OFF, STATE_ON
from .const import DOMAIN, LOGGER, UPDATE_INTERVAL


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the MG SAIC binary sensors."""
    client = hass.data[DOMAIN].get(entry.entry_id)
    if client is None:
        LOGGER.error("Client not initialized")
        return

    try:
        vehicle_status = await client.get_vehicle_status()
        LOGGER.debug("Vehicle Status: %s", vehicle_status)
    except Exception as e:
        LOGGER.error("Error connecting to MG SAIC API: %s", e)
        return

    sensors = [
        SAICMGBinarySensor(
            client,
            entry,
            "Driver Door",
            "driverDoor",
            "basicVehicleStatus",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
        ),
        SAICMGBinarySensor(
            client,
            entry,
            "Driver Window",
            "driverWindow",
            "basicVehicleStatus",
            BinarySensorDeviceClass.WINDOW,
            "mdi:car-door",
        ),
        SAICMGBinarySensor(
            client,
            entry,
            "Passenger Door",
            "passengerDoor",
            "basicVehicleStatus",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
        ),
        SAICMGBinarySensor(
            client,
            entry,
            "Passenger Window",
            "passengerWindow",
            "basicVehicleStatus",
            BinarySensorDeviceClass.WINDOW,
            "mdi:car-door",
        ),
        SAICMGBinarySensor(
            client,
            entry,
            "Rear Left Door",
            "rearLeftDoor",
            "basicVehicleStatus",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
        ),
        SAICMGBinarySensor(
            client,
            entry,
            "Rear Left Window",
            "rearLeftWindow",
            "basicVehicleStatus",
            BinarySensorDeviceClass.WINDOW,
            "mdi:car-door",
        ),
        SAICMGBinarySensor(
            client,
            entry,
            "Rear Right Door",
            "rearRightDoor",
            "basicVehicleStatus",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
        ),
        SAICMGBinarySensor(
            client,
            entry,
            "Rear Right Window",
            "rearRightWindow",
            "basicVehicleStatus",
            BinarySensorDeviceClass.WINDOW,
            "mdi:car-door",
        ),
        SAICMGBinarySensor(
            client,
            entry,
            "Sun Roof Status",
            "sunroofStatus",
            "basicVehicleStatus",
            BinarySensorDeviceClass.WINDOW,
            "mdi:car-door",
        ),
        SAICMGBinarySensor(
            client,
            entry,
            "Bonnet Status",
            "bonnetStatus",
            "basicVehicleStatus",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
        ),
        SAICMGBinarySensor(
            client,
            entry,
            "Boot Status",
            "bootStatus",
            "basicVehicleStatus",
            BinarySensorDeviceClass.DOOR,
            "mdi:car-door",
        ),
        SAICMGBinarySensor(
            client,
            entry,
            "Lock Status",
            "lockStatus",
            "basicVehicleStatus",
            BinarySensorDeviceClass.LOCK,
            "mdi:car-door-lock",
        ),
    ]
    async_add_entities(sensors, update_before_add=True)


class SAICMGBinarySensor(BinarySensorEntity):
    def __init__(self, client, entry, name, field, status_type, device_class, icon):
        self.client = client
        self._name = name
        self._field = field
        self._status_type = status_type
        self._state = None
        self._device_class = device_class
        self._icon = icon
        self._unique_id = f"{entry.entry_id}_{client.vin}_{field}"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"MG SAIC {self._name}"

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        # For lock status, 1 means locked (on), 0 means unlocked (off)
        if self._field == "lockStatus":
            return self._state == 0
        return bool(self._state)

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return self._device_class

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._icon

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.client.vin)},
            "name": f"MG SAIC {self.client.vin}",
            "manufacturer": "MG SAIC",
        }

    @property
    def state(self):
        """Return the state of the sensor."""
        return STATE_ON if self.is_on else STATE_OFF

    async def async_update(self):
        """Fetch new state data for the sensor."""
        try:
            status = await self.client.get_vehicle_status()

            # Check for generic response and discard it if necessary
            if self._is_generic_response(status):
                LOGGER.debug("Discarding generic response for %s", self._name)
                return

            status_data = getattr(status, self._status_type, None)
            LOGGER.debug("Status data for %s: %s", self._name, status_data)
            if status_data:
                raw_value = getattr(status_data, self._field, None)
                if raw_value is not None:
                    self._state = (
                        int(raw_value)
                        if self._field == "lockStatus"
                        else bool(raw_value)
                    )
            else:
                LOGGER.error("No status data for %s", self._name)
            self.async_write_ha_state()
        except Exception as e:
            LOGGER.error("Error connecting to MG SAIC API: %s", e)

    def _is_generic_response(self, status):
        """Check if the response is generic."""
        if (
            hasattr(status, "basicVehicleStatus")
            and status.basicVehicleStatus.fuelRange == 0
            and status.basicVehicleStatus.fuelRangeElec == 0
            and status.basicVehicleStatus.mileage == 0
        ):
            return True
        return False

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self.hass.helpers.event.async_track_time_interval(
                self.async_update, UPDATE_INTERVAL
            )
        )
