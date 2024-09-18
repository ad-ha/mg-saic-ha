from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN, LOGGER


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MG SAIC binary sensors."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]

    try:
        if not coordinator.data["info"] or not coordinator.data["status"]:
            LOGGER.error("Failed to retrieve vehicle info or status.")
            return

        vin_info = coordinator.data["info"][0]

        binary_sensors = [
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Door Front Left",
                "driverDoor",
                BinarySensorDeviceClass.DOOR,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Window Front Left",
                "driverWindow",
                BinarySensorDeviceClass.WINDOW,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Door Front Right",
                "passengerDoor",
                BinarySensorDeviceClass.DOOR,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Window Front Right",
                "passengerWindow",
                BinarySensorDeviceClass.WINDOW,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Door Rear Left",
                "rearLeftDoor",
                BinarySensorDeviceClass.DOOR,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Window Rear Left",
                "rearLeftWindow",
                BinarySensorDeviceClass.WINDOW,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Door Rear Right",
                "rearRightDoor",
                BinarySensorDeviceClass.DOOR,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Window Rear Right",
                "rearRightWindow",
                BinarySensorDeviceClass.WINDOW,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Sun Roof Status",
                "sunroofStatus",
                BinarySensorDeviceClass.WINDOW,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Bonnet Status",
                "bonnetStatus",
                BinarySensorDeviceClass.DOOR,
                "mdi:car",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Boot Status",
                "bootStatus",
                BinarySensorDeviceClass.DOOR,
                "mdi:car-back",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Lock Status",
                "lockStatus",
                BinarySensorDeviceClass.LOCK,
                "mdi:car-key",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "HVAC Status",
                "remoteClimateStatus",
                BinarySensorDeviceClass.RUNNING,
                "mdi:air-conditioner",
            ),
        ]

        # Now add the charging-related binary sensors
        if "charging" in coordinator.data and coordinator.data["charging"]:
            charging_binary_sensors = [
                SAICMGChargingBinarySensor(
                    coordinator,
                    entry,
                    "Charging Gun State",
                    "chargingGunState",
                    BinarySensorDeviceClass.PLUG,
                    "mdi:ev-plug-type2",
                    "rvsChargeStatus",
                ),
            ]

            binary_sensors.extend(charging_binary_sensors)

        async_add_entities(binary_sensors, update_before_add=True)

    except Exception as e:
        LOGGER.error("Error setting up MG SAIC binary sensors: %s", e)


class SAICMGBinarySensor(BinarySensorEntity, RestoreEntity):
    """Representation of a MG SAIC binary sensor."""

    def __init__(self, coordinator, entry, name, field, device_class, icon):
        """Initialize the binary sensor."""
        self.coordinator = coordinator
        self._name = name
        self._field = field
        self._device_class = device_class
        self._icon = icon
        self._state = None
        vin_info = self.coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}_binary_sensor"

    @property
    def unique_id(self):
        """Return the unique ID of the binary sensor."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the binary sensor."""
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    @property
    def device_class(self):
        """Return the device class of this binary sensor."""
        return self._device_class

    @property
    def icon(self):
        """Return the icon to use in the frontend."""
        return self._icon

    @property
    def device_info(self):
        """Return device information about this binary sensor."""
        vin_info = self.coordinator.data["info"][0]
        return {
            "identifiers": {(DOMAIN, vin_info.vin)},
            "name": f"{vin_info.brandName} {vin_info.modelName}",
            "manufacturer": vin_info.brandName,
            "model": vin_info.modelName,
            "serial_number": vin_info.vin,
        }

    async def async_update(self):
        """Fetch new state data for the binary sensor."""
        try:
            status_data = getattr(
                self.coordinator.data["status"], "basicVehicleStatus", None
            )
            if status_data:
                value = getattr(status_data, self._field, None)
                if value is not None:
                    if self._field == "lockStatus":
                        # 1 means locked, 0 means unlocked
                        self._state = value == 0
                    else:
                        self._state = bool(value)
                else:
                    LOGGER.warning(
                        "Field %s not found in status data for sensor %s",
                        self._field,
                        self._name,
                    )
            else:
                LOGGER.error("No status data for %s", self._name)
            self.async_write_ha_state()
        except Exception as e:
            LOGGER.error("Error updating binary sensor %s: %s", self._name, e)


class SAICMGChargingBinarySensor(SAICMGBinarySensor):
    """Representation of a MG SAIC charging binary sensor."""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        field,
        device_class,
        icon,
        data_source="chrgMgmtData",
    ):
        """Initialize the charging binary sensor."""
        super().__init__(coordinator, entry, name, field, device_class, icon)
        self._data_source = data_source
        self._unique_id = f"{self._unique_id}_charging"

    async def async_update(self):
        """Fetch new state data for the charging binary sensor."""
        try:
            charging_data = getattr(
                self.coordinator.data["charging"], self._data_source, None
            )
            if charging_data:
                value = getattr(charging_data, self._field, None)
                if value is not None:
                    if self._field == "chargingGunState":
                        # Assuming 0 means disconnected, 1 means connected
                        self._state = value == 1
                    else:
                        self._state = bool(value)
                else:
                    LOGGER.warning(
                        "Field %s not found in charging data for sensor %s",
                        self._field,
                        self._name,
                    )
            else:
                LOGGER.error("No charging data for %s", self._name)
            self.async_write_ha_state()
        except Exception as e:
            LOGGER.error("Error updating charging binary sensor %s: %s", self._name, e)
