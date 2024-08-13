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
        if not coordinator.data.get("info") or not coordinator.data.get("status"):
            LOGGER.error("Failed to retrieve vehicle info or status.")
            return

        vehicle_info = coordinator.data["info"]
        vehicle_status = coordinator.data["status"]

        sensors = [
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Door Front Left",
                "driverDoor",
                "basicVehicleStatus",
                BinarySensorDeviceClass.DOOR,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Window Front Left",
                "driverWindow",
                "basicVehicleStatus",
                BinarySensorDeviceClass.WINDOW,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Door Front Right",
                "passengerDoor",
                "basicVehicleStatus",
                BinarySensorDeviceClass.DOOR,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Window Front Right",
                "passengerWindow",
                "basicVehicleStatus",
                BinarySensorDeviceClass.WINDOW,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Door Rear Left",
                "rearLeftDoor",
                "basicVehicleStatus",
                BinarySensorDeviceClass.DOOR,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Window Rear Left",
                "rearLeftWindow",
                "basicVehicleStatus",
                BinarySensorDeviceClass.WINDOW,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Door Rear Right",
                "rearRightDoor",
                "basicVehicleStatus",
                BinarySensorDeviceClass.DOOR,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Window Rear Right",
                "rearRightWindow",
                "basicVehicleStatus",
                BinarySensorDeviceClass.WINDOW,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Sun Roof Status",
                "sunroofStatus",
                "basicVehicleStatus",
                BinarySensorDeviceClass.WINDOW,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Bonnet Status",
                "bonnetStatus",
                "basicVehicleStatus",
                BinarySensorDeviceClass.DOOR,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Boot Status",
                "bootStatus",
                "basicVehicleStatus",
                BinarySensorDeviceClass.DOOR,
                "mdi:car-door",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "Lock Status",
                "lockStatus",
                "basicVehicleStatus",
                BinarySensorDeviceClass.LOCK,
                "mdi:car-door-lock",
            ),
            SAICMGBinarySensor(
                coordinator,
                entry,
                "HVAC Status",
                "remoteClimateStatus",
                "basicVehicleStatus",
                BinarySensorDeviceClass.RUNNING,
                "mdi:air-conditioner",
            ),
        ]

        # Add all non-charging sensors first
        async_add_entities(sensors, update_before_add=True)

        # Now add the charging-related binary sensors separately, wrapped in a try-except block
        try:
            if coordinator.data and "charging" in coordinator.data:
                charging_sensors = [
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

                # Add charging sensors if they are available
                async_add_entities(charging_sensors, update_before_add=True)
            else:
                LOGGER.error("Failed to retrieve charging info.")
        except Exception as e:
            LOGGER.error("Error setting up MG SAIC charging binary sensors: %s", e)

    except Exception as e:
        LOGGER.error("Error setting up MG SAIC binary sensors: %s", e)


class SAICMGBinarySensor(BinarySensorEntity, RestoreEntity):
    """Binary sensor for MG SAIC vehicles."""

    def __init__(
        self, coordinator, entry, name, field, status_type, device_class, icon
    ):
        """Initialize the binary sensor."""
        self.coordinator = coordinator
        self._name = name
        self._field = field
        self._status_type = status_type
        self._device_class = device_class
        self._icon = icon
        self._state = None
        vin_info = coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        """Return the name of the binary sensor."""
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        if self._field == "lockStatus":
            # 1 means locked, 0 means unlocked
            return self._state == 0
        return self._state

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return self._device_class

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return self._icon

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

    async def async_update(self):
        """Fetch new state data for the binary sensor."""
        try:
            status_data = getattr(
                self.coordinator.data["status"].basicVehicleStatus,
                self._status_type,
                None,
            )
            if status_data:
                self._state = bool(getattr(status_data, self._field, 0))
            self.async_write_ha_state()
        except Exception as e:
            LOGGER.error("Error updating binary sensor %s: %s", self._name, e)

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_listener(self.async_update))
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._state = last_state.state == "on"


class SAICMGChargingBinarySensor(BinarySensorEntity, RestoreEntity):
    """Representation of a MG SAIC charging status binary sensor."""

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
        """Initialize the binary sensor."""
        self.coordinator = coordinator
        self._name = name
        self._field = field
        self._device_class = device_class
        self._icon = icon
        self._data_source = data_source
        self._is_on = False
        vin_info = self.coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}_charge"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        """Return the name of the binary sensor."""
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._is_on

    @property
    def device_class(self):
        """Return the class of this binary sensor."""
        return self._device_class

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return self._icon

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

    async def async_update(self):
        """Fetch new state data for the binary sensor."""
        try:
            charging_data = getattr(
                self.coordinator.data["charging"], self._data_source, None
            )
            if charging_data:
                raw_value = getattr(charging_data, self._field, None)
                if raw_value is not None:
                    self._is_on = bool(raw_value)
                else:
                    LOGGER.error("Field %s not found in charging data.", self._field)
            else:
                LOGGER.error("No charging data available for %s", self._name)
            self.async_write_ha_state()
        except Exception as e:
            LOGGER.error("Error updating charging binary sensor %s: %s", self._name, e)

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == "on"
