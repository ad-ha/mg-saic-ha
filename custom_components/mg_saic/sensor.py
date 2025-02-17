# File: sensor.py

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfPressure,
    UnitOfEnergy,
    UnitOfTime,
    UnitOfPower,
    UnitOfSpeed,
)
from .const import (
    DOMAIN,
    LOGGER,
    PRESSURE_TO_BAR,
    DATA_DECIMAL_CORRECTION,
    DATA_DECIMAL_CORRECTION_SOC,
    CHARGING_CURRENT_FACTOR,
    CHARGING_VOLTAGE_FACTOR,
    DATA_100_DECIMAL_CORRECTION,
)
from .utils import create_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MG SAIC sensors."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]

    try:
        if not coordinator.data.get("info"):
            LOGGER.error("Failed to retrieve vehicle info.")
            return

        vin_info = coordinator.vin_info
        vehicle_type = coordinator.vehicle_type

        sensors = [
            # Basic Vehicle Sensors
            SAICMGVehicleSensor(
                coordinator,
                entry,
                "Ancillary Battery Voltage",
                "batteryVoltage",
                "basicVehicleStatus",
                SensorDeviceClass.VOLTAGE,
                UnitOfElectricPotential.VOLT,
                "mdi:car-battery",
                "measurement",
                DATA_DECIMAL_CORRECTION,
                "status",
            ),
            SAICMGVehicleDetailSensor(
                coordinator,
                entry,
                "Brand",
                "brandName",
                "info",
            ),
            SAICMGVehicleSensor(
                coordinator,
                entry,
                "Exterior Temperature",
                "exteriorTemperature",
                "basicVehicleStatus",
                SensorDeviceClass.TEMPERATURE,
                UnitOfTemperature.CELSIUS,
                "mdi:thermometer",
                "measurement",
                1.0,
                "status",
            ),
            SAICMGVehicleSensor(
                coordinator,
                entry,
                "Interior Temperature",
                "interiorTemperature",
                "basicVehicleStatus",
                SensorDeviceClass.TEMPERATURE,
                UnitOfTemperature.CELSIUS,
                "mdi:thermometer",
                "measurement",
                1.0,
                "status",
            ),
            SAICMGVehicleSensor(
                coordinator,
                entry,
                "Last Key Seen",
                "lastKeySeen",
                "basicVehicleStatus",
                None,
                None,
                "mdi:key",
                None,
                1.0,
                "status",
            ),
            SAICMGTimestampSensor(
                coordinator,
                entry,
                "Last Powered On",
                "last_powered_on",
                SensorDeviceClass.TIMESTAMP,
                "mdi:power-on",
                "last_powered_on_time",
            ),
            SAICMGTimestampSensor(
                coordinator,
                entry,
                "Last Powered Off",
                "last_powered_off",
                SensorDeviceClass.TIMESTAMP,
                "mdi:power-off",
                "last_powered_off_time",
            ),
            SAICMGLastUpdateSensor(
                coordinator,
                entry,
                "Last Update Time",
                SensorDeviceClass.TIMESTAMP,
                None,
                "mdi:update",
                None,
                None,
            ),
            SAICMGTimestampSensor(
                coordinator,
                entry,
                "Last Vehicle Activity",
                "last_vehicle_activity",
                SensorDeviceClass.TIMESTAMP,
                "mdi:car-clock",
                "last_vehicle_activity",
            ),
            SAICMGMileageSensor(
                coordinator,
                entry,
                "Mileage",
                "mileage",
                "basicVehicleStatus",
                "rvsChargeStatus",
                SensorDeviceClass.DISTANCE,
                UnitOfLength.KILOMETERS,
                "mdi:counter",
                "total_increasing",
                DATA_DECIMAL_CORRECTION,
                "status",
            ),
            SAICMGNextUpdateSensor(
                coordinator,
                entry,
                "Next Update Time",
                SensorDeviceClass.TIMESTAMP,
                None,
                "mdi:update",
                None,
                None,
            ),
            SAICMGVehicleDetailSensor(
                coordinator,
                entry,
                "Model",
                "modelName",
                "info",
            ),
            SAICMGVehicleDetailSensor(
                coordinator,
                entry,
                "Model Year",
                "modelYear",
                "info",
            ),
            SAICMGVehicleSensor(
                coordinator,
                entry,
                "Power Mode",
                "powerMode",
                "basicVehicleStatus",
                None,
                None,
                "mdi:power-settings",
                None,
                1.0,
                "status",
            ),
            SAICMGVehicleSpeedSensor(
                coordinator,
                entry,
                "Speed",
                "speed",
                "gpsPosition",
                SensorDeviceClass.SPEED,
                UnitOfSpeed.KILOMETERS_PER_HOUR,
                "mdi:speedometer",
                "measurement",
                DATA_DECIMAL_CORRECTION,
                "status",
            ),
            SAICMGVehicleSensor(
                coordinator,
                entry,
                "Tyre Pressure Front Left",
                "frontLeftTyrePressure",
                "basicVehicleStatus",
                SensorDeviceClass.PRESSURE,
                UnitOfPressure.BAR,
                "mdi:car-tire-alert",
                "measurement",
                PRESSURE_TO_BAR,
                "status",
            ),
            SAICMGVehicleSensor(
                coordinator,
                entry,
                "Tyre Pressure Front Right",
                "frontRightTyrePressure",
                "basicVehicleStatus",
                SensorDeviceClass.PRESSURE,
                UnitOfPressure.BAR,
                "mdi:car-tire-alert",
                "measurement",
                PRESSURE_TO_BAR,
                "status",
            ),
            SAICMGVehicleSensor(
                coordinator,
                entry,
                "Tyre Pressure Rear Left",
                "rearLeftTyrePressure",
                "basicVehicleStatus",
                SensorDeviceClass.PRESSURE,
                UnitOfPressure.BAR,
                "mdi:car-tire-alert",
                "measurement",
                PRESSURE_TO_BAR,
                "status",
            ),
            SAICMGVehicleSensor(
                coordinator,
                entry,
                "Tyre Pressure Rear Right",
                "rearRightTyrePressure",
                "basicVehicleStatus",
                SensorDeviceClass.PRESSURE,
                UnitOfPressure.BAR,
                "mdi:car-tire-alert",
                "measurement",
                PRESSURE_TO_BAR,
                "status",
            ),
        ]

        if vehicle_type in ["PHEV", "HEV", "ICE"]:
            # PHEV, HEV, ICE Sensors
            sensors.append(
                SAICMGVehicleSensor(
                    coordinator,
                    entry,
                    "Fuel Level",
                    "fuelLevelPrc",
                    "basicVehicleStatus",
                    SensorDeviceClass.BATTERY,
                    PERCENTAGE,
                    "mdi:gas-station",
                    "measurement",
                    1.0,
                    "status",
                ),
            )

            sensors.append(
                SAICMGVehicleSensor(
                    coordinator,
                    entry,
                    "Fuel Range",
                    "fuelRange",
                    "basicVehicleStatus",
                    SensorDeviceClass.DISTANCE,
                    UnitOfLength.KILOMETERS,
                    "mdi:gas-station",
                    "measurement",
                    DATA_DECIMAL_CORRECTION,
                    "status",
                ),
            )

        if vehicle_type in ["BEV", "PHEV", "HEV"]:
            # BEV, PHEV, HEV Sensors
            sensors.append(
                SAICMGElectricRangeSensor(
                    coordinator,
                    entry,
                    "Electric Range",
                    "fuelRangeElec",
                    "basicVehicleStatus",
                    "rvsChargeStatus",
                    SensorDeviceClass.DISTANCE,
                    UnitOfLength.KILOMETERS,
                    "mdi:car-electric",
                    "measurement",
                    DATA_DECIMAL_CORRECTION,
                    "status",
                ),
            )

            sensors.append(
                SAICMGSOCSensor(
                    coordinator,
                    entry,
                    "State of Charge",
                    "extendedData1",
                    "bmsPackSOCDsp",
                    "basicVehicleStatus",
                    SensorDeviceClass.BATTERY,
                    PERCENTAGE,
                    "mdi:battery",
                    "measurement",
                    "charging",
                )
            )

            sensors.append(
                SAICMGChargingSensor(
                    coordinator,
                    entry,
                    "Total Battery Capacity",
                    "totalBatteryCapacity",
                    SensorDeviceClass.ENERGY,
                    UnitOfEnergy.KILO_WATT_HOUR,
                    "mdi:battery-high",
                    "total",
                    DATA_DECIMAL_CORRECTION,
                    "rvsChargeStatus",
                    "charging",
                )
            )

        if vehicle_type in ["BEV", "PHEV"]:
            # BEV, PHEV Sensors
            sensors.extend(
                [
                    SAICMGChargingSensor(
                        coordinator,
                        entry,
                        "Added Electric Range",
                        "chrgngAddedElecRng",
                        SensorDeviceClass.DISTANCE,
                        UnitOfLength.KILOMETERS,
                        "mdi:map-marker-distance",
                        "measurement",
                        DATA_DECIMAL_CORRECTION,
                        "chrgMgmtData",
                        "charging",
                    ),
                    SAICMGChargingCurrentSensor(
                        coordinator,
                        entry,
                        "Charging Current",
                        "bmsPackCrnt",
                        SensorDeviceClass.CURRENT,
                        "A",
                        "mdi:current-ac",
                        "measurement",
                        CHARGING_CURRENT_FACTOR,
                        "chrgMgmtData",
                        "charging",
                    ),
                    SAICMGChargingCurrentLimitSensor(
                        coordinator,
                        entry,
                        "Charging Current Limit",
                        "bmsAltngChrgCrntDspCmd",
                        None,
                        None,
                        "mdi:current-ac",
                        None,
                        1.0,
                        "chrgMgmtData",
                        "charging",
                    ),
                    SAICMGChargingSensor(
                        coordinator,
                        entry,
                        "Charging Duration",
                        "chargingDuration",
                        SensorDeviceClass.DURATION,
                        UnitOfTime.MINUTES,
                        "mdi:timer-outline",
                        "measurement",
                        DATA_100_DECIMAL_CORRECTION,
                        "rvsChargeStatus",
                        "charging",
                    ),
                    SAICMGChargingPowerSensor(
                        coordinator,
                        entry,
                        "Charging Power",
                        SensorDeviceClass.POWER,
                        UnitOfPower.KILO_WATT,
                        "mdi:flash",
                        "measurement",
                        "chrgMgmtData",
                        "charging",
                    ),
                    SAICMGChargingSensor(
                        coordinator,
                        entry,
                        "Charging Status",
                        "bmsChrgSts",
                        None,
                        None,
                        "mdi:battery-charging",
                        None,
                        1.0,
                        "chrgMgmtData",
                        "charging",
                    ),
                    SAICMGChargingSensor(
                        coordinator,
                        entry,
                        "Charging Voltage",
                        "bmsPackVol",
                        SensorDeviceClass.VOLTAGE,
                        UnitOfElectricPotential.VOLT,
                        "mdi:flash",
                        "measurement",
                        CHARGING_VOLTAGE_FACTOR,
                        "chrgMgmtData",
                        "charging",
                    ),
                    SAICMGChargingSensor(
                        coordinator,
                        entry,
                        "Estimated Range After Charging",
                        "bmsEstdElecRng",
                        SensorDeviceClass.DISTANCE,
                        UnitOfLength.KILOMETERS,
                        "mdi:map-marker-distance",
                        "measurement",
                        1.0,
                        "chrgMgmtData",
                        "charging",
                    ),
                    SAICMGInstantPowerSensor(
                        coordinator,
                        entry,
                        "Instant Power",
                        SensorDeviceClass.POWER,
                        UnitOfPower.KILO_WATT,
                        "mdi:lightning-bolt-circle",
                        "measurement",
                        "chrgMgmtData",
                        "charging",
                    ),
                    SAICMGChargingSensor(
                        coordinator,
                        entry,
                        "Mileage Since Last Charge",
                        "mileageSinceLastCharge",
                        SensorDeviceClass.DISTANCE,
                        UnitOfLength.KILOMETERS,
                        "mdi:map-marker-distance",
                        "measurement",
                        DATA_DECIMAL_CORRECTION,
                        "rvsChargeStatus",
                        "charging",
                    ),
                    SAICMGChargingSensor(
                        coordinator,
                        entry,
                        "Power Usage Since Last Charge",
                        "powerUsageSinceLastCharge",
                        SensorDeviceClass.ENERGY,
                        UnitOfEnergy.KILO_WATT_HOUR,
                        "mdi:flash",
                        "total_increasing",
                        DATA_DECIMAL_CORRECTION,
                        "rvsChargeStatus",
                        "charging",
                    ),
                    SAICMGChargingSensor(
                        coordinator,
                        entry,
                        "Remaining Charging Time",
                        "chrgngRmnngTime",
                        SensorDeviceClass.DURATION,
                        UnitOfTime.MINUTES,
                        "mdi:timer-sand",
                        "measurement",
                        1.0,
                        "chrgMgmtData",
                        "charging",
                    ),
                    SAICMGChargingSensor(
                        coordinator,
                        entry,
                        "Target SOC",
                        "bmsOnBdChrgTrgtSOCDspCmd",
                        SensorDeviceClass.BATTERY,
                        PERCENTAGE,
                        "mdi:battery-charging-100",
                        "measurement",
                        1.0,
                        "chrgMgmtData",
                        "charging",
                    ),
                ]
            )

        if coordinator.has_heated_seats:
            sensors.extend(
                [
                    SAICMGHeatedSeatLevelSensor(
                        coordinator,
                        entry,
                        "Front Left Heated Seat Level",
                        "frontLeftSeatHeatLevel",
                        None,
                        None,
                        "mdi:car-seat-heater",
                        None,
                        None,
                        "basicVehicleStatus",
                        "status",
                    ),
                    SAICMGHeatedSeatLevelSensor(
                        coordinator,
                        entry,
                        "Front Right Heated Seat Level",
                        "frontRightSeatHeatLevel",
                        None,
                        None,
                        "mdi:car-seat-heater",
                        None,
                        None,
                        "basicVehicleStatus",
                        "status",
                    ),
                ]
            )

        if coordinator.has_battery_heating:
            sensors.append(
                SAICMGChargingSensor(
                    coordinator,
                    entry,
                    "Battery Heating Status",
                    "bmsPTCHeatResp",
                    None,
                    None,
                    "mdi:heat-wave",
                    None,
                    1.0,
                    "chrgMgmtData",
                    "charging",
                ),
            )

        # Add sensors
        async_add_entities(sensors, update_before_add=True)

    except Exception as e:
        LOGGER.error("Error setting up MG SAIC sensors: %s", e)


# GENERAL VEHICLE DETAIL SENSORS
class SAICMGMileageSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Mileage, uses data from both VehicleStatusResp and ChrgMgmtDataResp."""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        field,
        status_type,
        charging_status_type,
        device_class,
        unit,
        icon,
        state_class,
        factor,
        data_type,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field = field
        self._status_type = status_type
        self._charging_status_type = charging_status_type
        self._factor = factor
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        self._data_type = data_type
        vin_info = self.coordinator.vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}"

        self._device_info = create_device_info(coordinator, entry.entry_id)
        self._vehicle_type = coordinator.vehicle_type

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.vin_info
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        # This sensor depends on both 'status' and 'charging' data
        # Since ICE vehicles only have 'status' data, check vehicle type
        if self._vehicle_type == "ICE":
            return (
                self.coordinator.last_update_success
                and self.coordinator.data.get("status") is not None
            )
        elif self._vehicle_type in ["PHEV", "HEV", "BEV"]:
            return (
                self.coordinator.last_update_success
                and self.coordinator.data.get("status") is not None
                and self.coordinator.data.get("charging") is not None
            )
        else:
            return False

    @property
    def native_value(self):
        # First, try to get mileage from VehicleStatusResp
        data = self.coordinator.data.get("status")
        mileage = None
        if data:
            status_data = getattr(data, self._status_type, None)
            if status_data:
                mileage = getattr(status_data, self._field, None)
                if mileage == 0 or mileage is None:
                    mileage = None  # Invalid or zero mileage
                else:
                    mileage = mileage * self._factor

        # If mileage is None or zero, try to get from ChrgMgmtDataResp
        if mileage is None:
            charging_data = self.coordinator.data.get("charging")
            if charging_data:
                charging_status_data = getattr(
                    charging_data, self._charging_status_type, None
                )
                if charging_status_data:
                    mileage = getattr(charging_status_data, self._field, None)
                    if mileage == 0 or mileage is None:
                        mileage = None
                    else:
                        mileage = mileage * self._factor

        return mileage

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


class SAICMGVehicleSensor(CoordinatorEntity, SensorEntity):
    """Representation of a MG SAIC vehicle sensor."""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        field,
        status_type,
        device_class,
        unit,
        icon,
        state_class,
        factor,
        data_type,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field = field
        self._status_type = status_type
        self._factor = factor
        self._data_type = data_type
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        vin_info = self.coordinator.vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.vin_info
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        required_data = self.coordinator.data.get(self._data_type)
        return self.coordinator.last_update_success and required_data is not None

    @property
    def native_value(self):
        data = self.coordinator.data.get(self._data_type)
        if data:
            if self._data_type == "status":
                status_data = getattr(data, self._status_type, None)
                if status_data:
                    raw_value = getattr(status_data, self._field, None)
                    if raw_value is not None:
                        # Handle special cases where raw_value might be invalid
                        if (
                            self._field
                            in ["interiorTemperature", "exteriorTemperature"]
                            and raw_value == -128
                        ):
                            LOGGER.debug(
                                "Sensor %s has invalid temperature value -128",
                                self._name,
                            )
                            return None
                        # Add mapping for powerMode
                        if self._field == "powerMode":
                            return {
                                0: "Off",
                                1: "Accessory",
                                2: "On",
                                3: "Start",
                            }.get(raw_value, f"Unknown ({raw_value})")

                        return raw_value * self._factor
            elif self._data_type == "charging":
                charging_data = getattr(data, self._status_type, None)
                if charging_data:
                    raw_value = getattr(charging_data, self._field, None)
                    if raw_value is not None:
                        return raw_value * self._factor
            elif self._data_type == "info":
                vin_info = data[0]
                raw_value = getattr(vin_info, self._field, None)
                if raw_value is not None:
                    return raw_value
        return None

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


class SAICMGVehicleDetailSensor(CoordinatorEntity, SensorEntity):
    """Representation of a sensor for MG SAIC vehicle details."""

    def __init__(self, coordinator, entry, name, field, data_type):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field = field
        self._data_type = data_type
        vin_info = self.coordinator.vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.vin_info
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        required_data = self.coordinator.data.get(self._data_type)
        return self.coordinator.last_update_success and required_data is not None

    @property
    def native_value(self):
        data = self.coordinator.data.get(self._data_type)
        if data:
            vin_info = data[0]
            raw_value = getattr(vin_info, self._field, None)
            if raw_value is not None:
                return raw_value
        return None

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


# STATUS SENSORS
class SAICMGHeatedSeatLevelSensor(CoordinatorEntity, SensorEntity):
    """Sensor to monitor the current heating level of a heated seat."""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        field,
        device_class,
        unit,
        icon,
        state_class,
        factor=None,
        data_source="basicVehicleStatus",
        data_type="status",
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field = field
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        self._factor = factor
        self._data_source = data_source
        self._data_type = data_type
        vin_info = self.coordinator.vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}_seat_heat_level"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        vin_info = self.coordinator.vin_info
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        data = self.coordinator.data.get(self._data_type)
        return self.coordinator.last_update_success and data is not None

    @property
    def native_value(self):
        """Return the mapped heating level value."""
        try:
            data = self.coordinator.data.get(self._data_type)
            if data:
                vehicle_status = getattr(data, self._data_source, None)
                if vehicle_status:
                    raw_value = getattr(vehicle_status, self._field, None)
                    return {0: "Off", 1: "Low", 2: "Medium", 3: "High"}.get(
                        raw_value, f"Unknown ({raw_value})"
                    )
        except Exception as e:
            LOGGER.error("Error retrieving heated seat level for %s: %s", self._name, e)
        return None

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


class SAICMGElectricRangeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Electric Range, uses data from both RvsChargeStatus and VehicleStatusResp."""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        field,
        status_type,
        charging_status_type,
        device_class,
        unit,
        icon,
        state_class,
        factor,
        data_type,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field = field
        self._status_type = status_type
        self._charging_status_type = charging_status_type
        self._factor = factor
        self._data_type = data_type
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        vin_info = self.coordinator.vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.vin_info
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        # This sensor depends on 'charging' and may fall back to 'status' data
        return self.coordinator.last_update_success and (
            self.coordinator.data.get("charging") is not None
            or self.coordinator.data.get("status") is not None
        )

    @property
    def native_value(self):
        """Return the electric range value, prioritizing charging data."""
        electric_range = None

        # First, try to get electric range from RvsChargeStatus
        charging_data = self.coordinator.data.get("charging")
        if charging_data:
            charging_status_data = getattr(
                charging_data, self._charging_status_type, None
            )
            if charging_status_data:
                raw_value = getattr(charging_status_data, self._field, None)
                if raw_value not in (None, 0):
                    electric_range = raw_value * self._factor

        # If electric_range is None or zero, try to get from VehicleStatusResp
        if electric_range is None:
            status_data = self.coordinator.data.get("status")
            if status_data:
                basic_status_data = getattr(status_data, self._status_type, None)
                if basic_status_data:
                    raw_value = getattr(basic_status_data, self._field, None)
                    if raw_value not in (None, 0):
                        electric_range = raw_value * self._factor

        return electric_range

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


class SAICMGInstantPowerSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Instant Power when the vehicle is powered on and driving."""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        device_class,
        unit,
        icon,
        state_class,
        data_source="chrgMgmtData",
        data_type="charging",
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._device_class = device_class
        self._unit = unit
        self._state_class = state_class
        self._icon = icon
        self._data_source = data_source
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        self._data_type = data_type
        vin_info = self.coordinator.vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_instant_power"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.vin_info
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        required_data = self.coordinator.data.get(self._data_type)
        return self.coordinator.last_update_success and required_data is not None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        try:
            charging_data = getattr(
                self.coordinator.data.get("charging"), self._data_source, None
            )
            if charging_data:
                # Check if the vehicle is driving
                status_data = self.coordinator.data.get("status")
                power_mode = getattr(status_data.basicVehicleStatus, "powerMode", None)
                if power_mode in [2, 3]:
                    # Get raw current and voltage
                    raw_current = getattr(charging_data, "bmsPackCrnt", None)
                    raw_voltage = getattr(charging_data, "bmsPackVol", None)

                    if raw_current is not None and raw_voltage is not None:
                        # Apply decoding to current and voltage
                        decoded_current = raw_current * CHARGING_CURRENT_FACTOR - 1000
                        decoded_voltage = raw_voltage * CHARGING_VOLTAGE_FACTOR

                        # Calculate power in kW
                        power = decoded_current * decoded_voltage / 1000.0

                        return round(power, 2)
                    else:
                        LOGGER.warning(
                            "Instant Power: Current or Voltage not available in charging data."
                        )
                        return None
                else:
                    return 0
            else:
                LOGGER.error("No charging data available for %s", self._name)
                return None

        except Exception as e:
            LOGGER.error(
                "Error retrieving instant power for sensor %s: %s", self._name, e
            )
            return None

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


class SAICMGSOCSensor(CoordinatorEntity, SensorEntity):
    """Sensor for State of Charge."""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        field_basic,
        field_charging,
        status_type,
        device_class,
        unit,
        icon,
        state_class,
        data_type,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field_basic = field_basic
        self._field_charging = field_charging
        self._status_type = status_type
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        self._data_type = data_type
        vin_info = self.coordinator.vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field_basic}_soc"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.vin_info
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        required_data = self.coordinator.data.get(self._data_type)
        return self.coordinator.last_update_success and required_data is not None

    @property
    def native_value(self):
        # First, try to get SOC from charging data (bmsPackSOCDsp)
        charging = self.coordinator.data.get("charging")
        soc = None
        if charging:
            charging_data = getattr(charging, "chrgMgmtData", None)
            if charging_data:
                soc = getattr(charging_data, self._field_charging, None)
                if soc is not None:
                    soc = soc * DATA_DECIMAL_CORRECTION_SOC

        # If SOC is None or invalid, try to get from basic vehicle status
        if soc is None:
            status = self.coordinator.data.get("status")
            if status:
                status_data = getattr(status, self._status_type, None)
                if status_data:
                    soc = getattr(status_data, self._field_basic, None)
                    if soc == -1 or soc == 0:
                        soc = None

        if soc is not None:
            return soc
        else:
            return None

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


# CHARGING SENSORS
class SAICMGChargingCurrentSensor(CoordinatorEntity, SensorEntity):
    """Representation of a MG SAIC charging current sensor"""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        field,
        device_class,
        unit,
        icon,
        state_class,
        factor=None,
        data_source="chrgMgmtData",
        data_type="charging",
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field = field
        self._device_class = device_class
        self._unit = unit
        self._state_class = state_class
        self._icon = icon
        self._factor = factor
        self._data_source = data_source
        self._data_type = data_type
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        vin_info = self.coordinator.vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}_charge"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.vin_info
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        required_data = self.coordinator.data.get(self._data_type)
        return self.coordinator.last_update_success and required_data is not None

    @property
    def native_value(self):
        """Return the state of the sensor"""
        try:
            charging_data = getattr(
                self.coordinator.data.get("charging"), self._data_source, None
            )
            if charging_data:
                charging_status = getattr(charging_data, "bmsChrgSts", None)

                if charging_status in [0, 5]:
                    return 0

                raw_value = getattr(charging_data, self._field, None)

                # Calculate Current
                if raw_value is not None and self._factor is not None:
                    calculated_value = 1000 - (raw_value * self._factor)
                    return round(calculated_value, 2)
                else:
                    return None
            else:
                LOGGER.error("No charging data available for %s", self._name)
                return None

        except Exception as e:
            LOGGER.error(
                "Error retrieving charging current sensor %s: %s",
                self._name,
                e,
                exc_info=True,
            )
            return None

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


class SAICMGChargingPowerSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Charging Power, calculated from voltage and current."""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        device_class,
        unit,
        icon,
        state_class,
        data_source="chrgMgmtData",
        data_type="charging",
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._device_class = device_class
        self._unit = unit
        self._state_class = state_class
        self._icon = icon
        self._data_source = data_source
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        self._data_type = data_type
        vin_info = self.coordinator.vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_charging_power"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.vin_info
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        required_data = self.coordinator.data.get(self._data_type)
        return self.coordinator.last_update_success and required_data is not None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        try:
            charging_data = getattr(
                self.coordinator.data.get("charging"), self._data_source, None
            )
            if charging_data:
                # Fetch the charging status to determine if the sensor should display data
                charging_status = getattr(charging_data, "bmsChrgSts", None)

                if charging_status in [0, 5]:
                    return 0

                # Get raw current and voltage
                raw_current = getattr(charging_data, "bmsPackCrnt", None)
                raw_voltage = getattr(charging_data, "bmsPackVol", None)

                if raw_current is not None and raw_voltage is not None:
                    # Apply decoding to current and voltage
                    decoded_current = 1000 - raw_current * CHARGING_CURRENT_FACTOR
                    decoded_voltage = raw_voltage * CHARGING_VOLTAGE_FACTOR

                    # Calculate power in kW
                    power = decoded_current * decoded_voltage / 1000.0

                    return round(power, 2)
                else:
                    return None
            else:
                LOGGER.error("No charging data available for %s", self._name)
                return None

        except Exception as e:
            LOGGER.error("Error retrieving charging power sensor %s: %s", self._name, e)
            return None

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


class SAICMGChargingSensor(CoordinatorEntity, SensorEntity):
    """Representation of a MG SAIC charging sensor."""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        field,
        device_class,
        unit,
        icon,
        state_class,
        factor=None,
        data_source="chrgMgmtData",
        data_type="charging",
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field = field
        self._device_class = device_class
        self._unit = unit
        self._state_class = state_class
        self._icon = icon
        self._factor = factor
        self._data_source = data_source
        self._data_type = data_type
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        vin_info = self.coordinator.vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}_charge"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.vin_info
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        required_data = self.coordinator.data.get(self._data_type)
        return self.coordinator.last_update_success and required_data is not None

    @property
    def native_value(self):
        """Return the state of the sensor."""
        try:
            charging_data = getattr(
                self.coordinator.data.get("charging"), self._data_source, None
            )
            raw_value = None

            if charging_data:
                # Fetch the charging status to determine if the sensor should display data
                charging_status = getattr(charging_data, "bmsChrgSts", None)

                # Apply the "Not charging" condition only for the specified sensors
                if self._field in [
                    "bmsPackVol",
                    "bmsPackCrnt",
                    "lastChargeEndingPower",
                    "bmsChrgOtptCrntReq",
                    "chargingDuration",
                    "chrgngRmnngTime",
                    "chrgngAddedElecRng",
                ]:
                    if charging_status in [0, 5]:
                        return 0
                    else:
                        raw_value = getattr(charging_data, self._field, None)
                        return (
                            raw_value * self._factor if raw_value is not None else None
                        )

                elif self._field == "bmsOnBdChrgTrgtSOCDspCmd":
                    # Map the target SOC values to percentages
                    raw_value = getattr(charging_data, self._field, None)
                    return {
                        1: 40,
                        2: 50,
                        3: 60,
                        4: 70,
                        5: 80,
                        6: 90,
                        7: 100,
                    }.get(raw_value, None)

                elif self._field == "bmsChrgSts":
                    # Map bmsChrgSts values to charging statuses (these are strings)
                    raw_value = getattr(charging_data, self._field, None)
                    return {
                        0: "Not Charging",
                        1: "Charging (AC)",
                        2: "Charging Finished",
                        3: "Charging",
                        4: "Fault Charging",
                        5: "Idle",
                        6: "Unrecognized Connection",
                        7: "Plugged In",
                        8: "Charging Stopped",
                        9: "Scheduled Charging",
                        10: "Charging (DC)",
                        11: "Super Offboard Charging",
                        12: "Charging",
                    }.get(raw_value, f"Unknown ({raw_value})")

                elif self._field == "bmsPTCHeatResp":
                    # Map bmsPTCHeatResp values to status strings
                    return {
                        0: "Off",
                        1: "On",
                        2: "Error",
                    }.get(raw_value, f"Unknown ({raw_value})")

                else:
                    # Handle other numeric fields
                    raw_value = getattr(charging_data, self._field, None)
                    return raw_value * self._factor if raw_value is not None else None

            if raw_value is None:
                LOGGER.warning("Field %s returned None in charging data.", self._field)
            else:
                LOGGER.error("No charging data available for %s", self._name)
                return None

        except Exception as e:
            LOGGER.error("Error retrieving charging sensor %s: %s", self._name, e)
            return None

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


class SAICMGChargingCurrentLimitSensor(CoordinatorEntity, SensorEntity):
    """Sensor to show the charging current limit."""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        field,
        device_class,
        unit,
        icon,
        state_class,
        factor=None,
        data_source="chrgMgmtData",
        data_type="charging",
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field = field
        self._device_class = device_class
        self._unit = unit
        self._icon = icon
        self._state_class = state_class
        self._factor = factor
        self._data_source = data_source
        self._data_type = data_type
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        vin_info = self.coordinator.vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}_current_limit"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.vin_info
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        required_data = self.coordinator.data.get(self._data_type)
        return self.coordinator.last_update_success and required_data is not None

    @property
    def native_value(self):
        """Return the current charging limit."""
        try:
            charging_data = getattr(
                self.coordinator.data.get("charging"), self._data_source, None
            )
            if charging_data:
                current_limit_code = getattr(charging_data, self._field, None)
                if current_limit_code is not None:
                    # Map the charging limit code to human-readable format
                    return {
                        0: "0A (Ignore)",
                        1: "6A",
                        2: "8A",
                        3: "16A",
                        4: "Max",
                    }.get(current_limit_code, f"Unknown ({current_limit_code})")
            return None
        except Exception as e:
            LOGGER.error(
                "Error retrieving charging current limit for %s: %s", self._name, e
            )
            return None

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


# LAST UPDATE TIME DATA SENSOR
class SAICMGLastUpdateSensor(CoordinatorEntity, SensorEntity):
    """Sensor to display the timestamp of the last successful data update."""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        device_class,
        unit,
        icon,
        state_class,
        data_type,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._device_class = device_class
        self._unit = unit
        self._icon = icon
        self._state_class = state_class
        self._data_type = data_type
        vin_info = self.coordinator.vin_info
        self._vin_info = vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_last_update_time"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return f"{self._vin_info.brandName} {self._vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        return (
            self.coordinator.last_update_success
            and hasattr(self.coordinator, "last_update_time")
            and self.coordinator.last_update_time is not None
        )

    @property
    def native_value(self):
        """Return the timestamp of the last successful data update."""
        return self.coordinator.last_update_time

    @property
    def device_class(self):
        return self._device_class

    @property
    def icon(self):
        return self._icon

    @property
    def native_unit_of_measurement(self):
        return self._unit

    @property
    def state_class(self):
        return self._state_class

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


# NEXT UPDATE TIME DATA SENSOR
class SAICMGNextUpdateSensor(CoordinatorEntity, SensorEntity):
    """Sensor to display the timestamp of the next scheduled data update."""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        device_class,
        unit,
        icon,
        state_class,
        data_type,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._device_class = device_class
        self._unit = unit
        self._icon = icon
        self._state_class = state_class
        self._data_type = data_type
        vin_info = self.coordinator.vin_info
        self._vin_info = vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_next_update_time"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        return f"{self._vin_info.brandName} {self._vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        return (
            self.coordinator.last_update_success
            and hasattr(self.coordinator, "next_update_time")
            and self.coordinator.next_update_time is not None
        )

    @property
    def native_value(self):
        """Return the timestamp of the next scheduled data update."""
        return self.coordinator.next_update_time

    @property
    def device_class(self):
        return self._device_class

    @property
    def icon(self):
        return self._icon

    @property
    def native_unit_of_measurement(self):
        return self._unit

    @property
    def state_class(self):
        return self._state_class

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


class SAICMGTimestampSensor(CoordinatorEntity, SensorEntity):
    """Representation of a timestamp sensor for MG SAIC vehicles."""

    def __init__(self, coordinator, entry, name, field, device_class, icon, attribute):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field = field
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attribute = attribute  # Attribute name to fetch from the coordinator
        vin_info = self.coordinator.vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        """Return the unique ID of the sensor."""
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        vin_info = self.coordinator.vin_info
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        return self.coordinator.last_update_success and self.native_value is not None

    @property
    def native_value(self):
        """Return the timestamp value from the coordinator."""
        try:
            return getattr(self.coordinator, self._attribute, None)
        except AttributeError as e:
            LOGGER.error(
                "Error retrieving attribute '%s' for sensor '%s': %s",
                self._attribute,
                self._name,
                e,
            )
            return None

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info


class SAICMGVehicleSpeedSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Vehicle Speed."""

    def __init__(
        self,
        coordinator,
        entry,
        name,
        field,
        status_type,
        device_class,
        unit,
        icon,
        state_class,
        factor,
        data_type,
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field = field
        self._status_type = status_type
        self._factor = factor
        self._data_type = data_type
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        vin_info = self.coordinator.vin_info
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        vin_info = self.coordinator.vin_info
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def available(self):
        """Return True if the entity is available."""
        required_data = self.coordinator.data.get(self._data_type)
        return self.coordinator.last_update_success and required_data is not None

    @property
    def native_value(self):
        """Return the speed value."""
        try:
            data = self.coordinator.data.get(self._data_type)
            if data:
                gps = getattr(data, self._status_type, None)
                if gps and gps.wayPoint:
                    speed = gps.wayPoint.speed
                    return speed * self._factor if speed else 0
        except AttributeError as e:
            LOGGER.error("Error retrieving speed for sensor '%s': %s", self._name, e)
        return None

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info
