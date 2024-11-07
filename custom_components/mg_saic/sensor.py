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
)
from .const import (
    DOMAIN,
    LOGGER,
    PRESSURE_TO_BAR,
    DATA_DECIMAL_CORRECTION,
    DATA_DECIMAL_CORRECTION_SOC,
    CHARGING_CURRENT_FACTOR,
    CHARGING_VOLTAGE_FACTOR,
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MG SAIC sensors."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]

    try:
        if not coordinator.data["info"] or not coordinator.data["status"]:
            LOGGER.error("Failed to retrieve vehicle info or status.")
            return

        vin_info = coordinator.data["info"][0]
        vehicle_type = coordinator.vehicle_type

        sensors = [
            # Basic Vehicle Sensors
            SAICMGVehicleSensor(
                coordinator,
                entry,
                "Battery Voltage",
                "batteryVoltage",
                "basicVehicleStatus",
                SensorDeviceClass.VOLTAGE,
                UnitOfElectricPotential.VOLT,
                "mdi:car-battery",
                "measurement",
                DATA_DECIMAL_CORRECTION,
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
            ),
            SAICMGVehicleDetailSensor(
                coordinator,
                entry,
                "Model Year",
                "modelYear",
            ),
            SAICMGVehicleDetailSensor(
                coordinator,
                entry,
                "Brand",
                "brandName",
            ),
            SAICMGVehicleDetailSensor(
                coordinator,
                entry,
                "Model",
                "modelName",
            ),
        ]

        if vehicle_type in ["PHEV", "HEV"]:
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
                ),
            )

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
                ),
            )

        if vehicle_type in ["BEV", "PHEV", "HEV"]:
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
                )
            )

            sensors.append(
                SAICMGVehicleSensor(
                    coordinator,
                    entry,
                    "Electric Range",
                    "fuelRangeElec",
                    "basicVehicleStatus",
                    SensorDeviceClass.DISTANCE,
                    "km",
                    "mdi:car-electric",
                    "measurement",
                    DATA_DECIMAL_CORRECTION,
                ),
            )

        if vehicle_type in ["BEV", "PHEV"]:
            sensors.extend(
                [
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
                    ),
                    SAICMGChargingSensor(
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
                        1.0,
                        "rvsChargeStatus",
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
                    ),
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
                        1.0,
                        "rvsChargeStatus",
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
                    ),
                    SAICMGChargingSensor(
                        coordinator,
                        entry,
                        "Battery Heating Status",
                        "bmsPTCHeatResp",
                        None,
                        None,
                        "mdi:fire",
                        None,
                        1.0,
                        "chrgMgmtData",
                    ),
                ]
            )

        # Add sensors
        async_add_entities(sensors, update_before_add=True)

    except Exception as e:
        LOGGER.error("Error setting up MG SAIC sensors: %s", e)


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
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field = field
        self._status_type = status_type
        self._factor = factor
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        vin_info = self.coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def native_value(self):
        data = self.coordinator.data.get("status")
        if data:
            status_data = getattr(data, self._status_type, None)
            if status_data:
                raw_value = getattr(status_data, self._field, None)
                if raw_value is not None:
                    # Handle special cases where raw_value might be invalid
                    if (
                        self._field in ["interiorTemperature", "exteriorTemperature"]
                        and raw_value == -128
                    ):
                        LOGGER.debug(
                            "Sensor %s has invalid temperature value -128", self._name
                        )
                        return None
                    return raw_value * self._factor
        return None

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
        vin_info = self.coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field_basic}_soc"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

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
        vin_info = self.coordinator.data["info"][0]
        return {
            "identifiers": {(DOMAIN, vin_info.vin)},
            "name": f"{vin_info.brandName} {vin_info.modelName}",
            "manufacturer": vin_info.brandName,
            "model": vin_info.modelName,
            "serial_number": vin_info.vin,
        }


class SAICMGVehicleDetailSensor(CoordinatorEntity, SensorEntity):
    """Representation of a sensor for MG SAIC vehicle details."""

    def __init__(self, coordinator, entry, name, field):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field = field
        vin_info = self.coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def native_value(self):
        vin_info = self.coordinator.data["info"][0]
        return getattr(vin_info, self._field, None)

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
    ):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._field = field  # "mileage"
        self._status_type = status_type  # "basicVehicleStatus"
        self._charging_status_type = charging_status_type  # "rvsChargeStatus"
        self._factor = factor  # DATA_DECIMAL_CORRECTION
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        vin_info = self.coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

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
        vin_info = self.coordinator.data["info"][0]
        return {
            "identifiers": {(DOMAIN, vin_info.vin)},
            "name": f"{vin_info.brandName} {vin_info.modelName}",
            "manufacturer": vin_info.brandName,
            "model": vin_info.modelName,
            "serial_number": vin_info.vin,
        }


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
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_state_class = state_class
        vin_info = self.coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}_charge"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

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
                        return 0  # Display 0 for these sensors when not charging
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
                        5: "Charging Finished",
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
        vin_info = self.coordinator.data["info"][0]
        return {
            "identifiers": {(DOMAIN, vin_info.vin)},
            "name": f"{vin_info.brandName} {vin_info.modelName}",
            "manufacturer": vin_info.brandName,
            "model": vin_info.modelName,
            "serial_number": vin_info.vin,
        }


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
        vin_info = self.coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_charging_power"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

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

                if charging_status in [0, 5]:  # Not charging or Charging Finished
                    return 0

                # Get raw current and voltage
                raw_current = getattr(charging_data, "bmsPackCrnt", None)
                raw_voltage = getattr(charging_data, "bmsPackVol", None)

                if raw_current is not None and raw_voltage is not None:
                    # Apply decoding to current and voltage
                    decoded_current = raw_current * CHARGING_CURRENT_FACTOR
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
        vin_info = self.coordinator.data["info"][0]
        return {
            "identifiers": {(DOMAIN, vin_info.vin)},
            "name": f"{vin_info.brandName} {vin_info.modelName}",
            "manufacturer": vin_info.brandName,
            "model": vin_info.modelName,
            "serial_number": vin_info.vin,
        }
