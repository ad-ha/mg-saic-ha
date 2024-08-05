# sensor.py

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfPressure,
)
from .const import DOMAIN, LOGGER


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the MG SAIC sensors."""
    client = hass.data[DOMAIN][entry.entry_id]

    try:
        vehicle_info = await client.get_vehicle_info()
        vehicle_status = await client.get_vehicle_status()

        if vehicle_info is None or vehicle_status is None:
            LOGGER.error("Failed to retrieve vehicle info or status.")
            return

        LOGGER.debug("Vehicle Info: %s", vehicle_info)
        LOGGER.debug("Vehicle Status: %s", vehicle_status)

        # Set brand and model from the vehicle info
        client.brand = vehicle_info[0].brandName
        client.model = vehicle_info[0].modelName

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
                vehicle_status,
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
                vehicle_status,
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
                vehicle_status,
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
                vehicle_status,
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
                vehicle_status,
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
                vehicle_status,
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
                vehicle_status,
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
                vehicle_status,
            ),
            SAICMGVehicleSensor(
                client,
                entry,
                "Tyre Pressure Front Left",
                "frontLeftTyrePressure",
                "basicVehicleStatus",
                UnitOfPressure.BAR,
                SensorDeviceClass.PRESSURE,
                "mdi:car-tire-alert",
                vehicle_status,
                0.04,
            ),
            SAICMGVehicleSensor(
                client,
                entry,
                "Tyre Pressure Front Right",
                "frontRightTyrePressure",
                "basicVehicleStatus",
                UnitOfPressure.BAR,
                SensorDeviceClass.PRESSURE,
                "mdi:car-tire-alert",
                vehicle_status,
                0.04,
            ),
            SAICMGVehicleSensor(
                client,
                entry,
                "Tyre Pressure Rear Left",
                "rearLeftTyrePressure",
                "basicVehicleStatus",
                UnitOfPressure.BAR,
                SensorDeviceClass.PRESSURE,
                "mdi:car-tire-alert",
                vehicle_status,
                0.04,
            ),
            SAICMGVehicleSensor(
                client,
                entry,
                "Tyre Pressure Rear Right",
                "rearRightTyrePressure",
                "basicVehicleStatus",
                UnitOfPressure.BAR,
                SensorDeviceClass.PRESSURE,
                "mdi:car-tire-alert",
                vehicle_status,
                0.04,
            ),
            # New Sensors for vehicle details
            SAICMGVehicleDetailSensor(
                client,
                entry,
                "Brand",
                "brandName",
                vehicle_info,
            ),
            SAICMGVehicleDetailSensor(
                client,
                entry,
                "Model",
                "modelName",
                vehicle_info,
            ),
            SAICMGVehicleDetailSensor(
                client,
                entry,
                "Model Year",
                "modelYear",
                vehicle_info,
            ),
        ]

        async_add_entities(sensors, update_before_add=True)

    except Exception as e:
        LOGGER.error("Error connecting to MG SAIC API: %s", e)

    # Separate block for charging sensors
    try:
        charging_info = await client.get_charging_info()
        if charging_info is None:
            LOGGER.warning("Charging information is not available at setup.")
        else:
            charging_sensors = [
                SAICMGChargingSensor(
                    client,
                    entry,
                    "Charging Status",
                    "chargingStatus",
                    charging_info,
                    None,
                    "mdi:battery-charging",
                ),
                SAICMGChargingSensor(
                    client,
                    entry,
                    "Charging State",
                    "chargingState",
                    charging_info,
                    None,
                    "mdi:car-electric",
                ),
                SAICMGChargingSensor(
                    client,
                    entry,
                    "Charging Power",
                    "chargingPower",
                    charging_info,
                    UnitOfPower.WATT,
                    "mdi:flash",
                ),
            ]
            async_add_entities(charging_sensors, update_before_add=True)
    except Exception as e:
        LOGGER.error("Error retrieving charging information: %s", e)


class SAICMGVehicleSensor(SensorEntity):
    """Sensor for general vehicle data."""

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
        status_data,
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
        self._status_data = status_data

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.client.brand} {self.client.model} {self._name}"

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
            "name": f"{self.client.brand} {self.client.model}",
            "manufacturer": f"{self.client.brand}",
            "model": f"{self.client.model}",
            "serial_number": f"{self.client.vin}",
        }

    async def async_update(self):
        """Fetch new state data for the sensor."""
        try:
            status_data = getattr(self._status_data, self._status_type, None)
            if status_data:
                raw_value = getattr(status_data, self._field, None)
                if raw_value is not None:
                    self._state = raw_value * self._factor
            else:
                LOGGER.error("No status data for %s", self._name)
            self.async_write_ha_state()
        except Exception as e:
            LOGGER.error("Error connecting to MG SAIC API: %s", e)


class SAICMGVehicleDetailSensor(SensorEntity):
    """Sensor for vehicle details."""

    def __init__(self, client, entry, name, field, vehicle_info):
        self.client = client
        self._name = name
        self._field = field
        self._state = None
        self._unique_id = f"{entry.entry_id}_{client.vin}_{field}"
        self._vehicle_info = vehicle_info

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.client.brand} {self.client.model} {self._name}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.client.vin)},
            "name": f"{self.client.brand} {self.client.model}",
            "manufacturer": f"{self.client.brand}",
            "model": f"{self.client.model}",
            "serial_number": f"{self.client.vin}",
        }

    async def async_update(self):
        """Fetch new state data for the sensor."""
        try:
            if self._vehicle_info:
                raw_value = getattr(self._vehicle_info[0], self._field, None)
                if raw_value is not None:
                    self._state = raw_value
                else:
                    LOGGER.error("No data for %s", self._name)
            self.async_write_ha_state()
        except Exception as e:
            LOGGER.error("Error connecting to MG SAIC API: %s", e)


class SAICMGChargingSensor(SensorEntity):
    """Sensor for charging-related data."""

    def __init__(self, client, entry, name, field, charging_data, unit, icon):
        self.client = client
        self._name = name
        self._field = field
        self._state = None
        self._unit = unit
        self._icon = icon
        self._unique_id = f"{entry.entry_id}_{client.vin}_{field}"
        self._charging_data = charging_data

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self.client.brand} {self.client.model} {self._name}"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return the icon of the sensor."""
        return self._icon

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.client.vin)},
            "name": f"{self.client.brand} {self.client.model}",
            "manufacturer": f"{self.client.brand}",
            "model": f"{self.client.model}",
            "serial_number": f"{self.client.vin}",
        }

    async def async_update(self):
        """Fetch new state data for the sensor."""
        try:
            # Fetch fresh charging data each update
            charging_data = await self.client.get_charging_info()
            LOGGER.debug("Charging data for %s: %s", self._name, charging_data)

            if charging_data:
                raw_value = getattr(charging_data, self._field, None)
                if raw_value is not None:
                    self._state = raw_value
            else:
                LOGGER.error("No charging data for %s", self._name)
            self.async_write_ha_state()
        except Exception as e:
            LOGGER.error("Error updating charging sensor: %s", e)
