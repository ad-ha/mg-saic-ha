from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfElectricPotential,
    UnitOfPressure,
)
from homeassistant.util.unit_system import UnitOfTemperature
from .const import DOMAIN, LOGGER, UPDATE_INTERVAL


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the MG SAIC sensors."""
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
        SAICMGVehicleSensor(
            client,
            entry,
            "Battery Voltage",
            "batteryVoltage",
            "basicVehicleStatus",
            UnitOfElectricPotential.VOLT,
            SensorDeviceClass.VOLTAGE,
            "mdi:car-battery",
            0.1,
        ),
        SAICMGVehicleSensor(
            client,
            entry,
            "Fuel Level",
            "fuelLevelPrc",
            "basicVehicleStatus",
            PERCENTAGE,
            SensorDeviceClass.BATTERY,
            "mdi:gas-station",
        ),
        SAICMGVehicleSensor(
            client,
            entry,
            "Fuel Range",
            "fuelRange",
            "basicVehicleStatus",
            UnitOfLength.KILOMETERS,
            SensorDeviceClass.DISTANCE,
            "mdi:car-electric",
            0.1,
        ),
        SAICMGVehicleSensor(
            client,
            entry,
            "Electric Range",
            "fuelRangeElec",
            "basicVehicleStatus",
            UnitOfLength.KILOMETERS,
            SensorDeviceClass.DISTANCE,
            "mdi:car-electric",
            0.1,
        ),
        SAICMGVehicleSensor(
            client,
            entry,
            "Mileage",
            "mileage",
            "basicVehicleStatus",
            UnitOfLength.KILOMETERS,
            SensorDeviceClass.DISTANCE,
            "mdi:counter",
            0.1,
        ),
        SAICMGVehicleSensor(
            client,
            entry,
            "EV Percentage",
            "extendedData1",
            "basicVehicleStatus",
            PERCENTAGE,
            SensorDeviceClass.BATTERY,
            "mdi:battery",
        ),
        SAICMGVehicleSensor(
            client,
            entry,
            "HVAC Status",
            "remoteClimateStatus",
            "basicVehicleStatus",
            None,
            None,
            "mdi:air-conditioner",
        ),
        SAICMGVehicleSensor(
            client,
            entry,
            "Interior Temperature",
            "interiorTemperature",
            "basicVehicleStatus",
            UnitOfTemperature.CELSIUS,
            SensorDeviceClass.TEMPERATURE,
            "mdi:thermometer",
        ),
        SAICMGVehicleSensor(
            client,
            entry,
            "Front Left Tyre Pressure",
            "frontLeftTyrePressure",
            "basicVehicleStatus",
            UnitOfPressure.BAR,
            SensorDeviceClass.PRESSURE,
            "mdi:car-tire-alert",
            0.04,
        ),
        SAICMGVehicleSensor(
            client,
            entry,
            "Front Right Tyre Pressure",
            "frontRightTyrePressure",
            "basicVehicleStatus",
            UnitOfPressure.BAR,
            SensorDeviceClass.PRESSURE,
            "mdi:car-tire-alert",
            0.04,
        ),
        SAICMGVehicleSensor(
            client,
            entry,
            "Rear Left Tyre Pressure",
            "rearLeftTyrePressure",
            "basicVehicleStatus",
            UnitOfPressure.BAR,
            SensorDeviceClass.PRESSURE,
            "mdi:car-tire-alert",
            0.04,
        ),
        SAICMGVehicleSensor(
            client,
            entry,
            "Rear Right Tyre Pressure",
            "rearRightTyrePressure",
            "basicVehicleStatus",
            UnitOfPressure.BAR,
            SensorDeviceClass.PRESSURE,
            "mdi:car-tire-alert",
            0.04,
        ),
    ]
    async_add_entities(sensors, update_before_add=True)


class SAICMGVehicleSensor(SensorEntity):
    def __init__(
        self,
        client,
        entry,
        name,
        field,
        status_type,
        unit,
        device_class,
        icon,
        factor=1,
    ):
        self.client = client
        self._name = name
        self._field = field
        self._status_type = status_type
        self._state = None
        self._unit = unit
        self._device_class = device_class
        self._icon = icon
        self._factor = factor
        self._unique_id = f"{entry.entry_id}_{client.vin}_{field}"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"MG SAIC {self._name}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

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
                    self._state = raw_value * self._factor
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
