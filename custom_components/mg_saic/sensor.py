from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import PERCENTAGE
from homeassistant.helpers.restore_state import RestoreEntity
from .const import DOMAIN, LOGGER, PRESSURE_TO_BAR, DATA_DECIMAL_CORRECTION


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MG SAIC sensors."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]

    try:
        if not coordinator.data["info"] or not coordinator.data["status"]:
            LOGGER.error("Failed to retrieve vehicle info or status.")
            return

        vin_info = coordinator.data["info"][0]
        vehicle_status = coordinator.data["status"]
        vehicle_type = coordinator.vehicle_type

        sensors = [
            SAICMGVehicleSensor(
                coordinator,
                entry,
                "Battery Voltage",
                "batteryVoltage",
                "basicVehicleStatus",
                SensorDeviceClass.VOLTAGE,
                "V",
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
                "°C",
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
                "°C",
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
                "bar",
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
                "bar",
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
                "bar",
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
                "bar",
                "mdi:car-tire-alert",
                "measurement",
                PRESSURE_TO_BAR,
            ),
            SAICMGVehicleSensor(
                coordinator,
                entry,
                "Mileage",
                "mileage",
                "basicVehicleStatus",
                SensorDeviceClass.DISTANCE,
                "km",
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
                    "km",
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
                    "%",
                    "mdi:gas-station",
                    "measurement",
                    1.0,
                ),
            )

        if vehicle_type in ["BEV", "PHEV"]:
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

            sensors.append(
                SAICMGBatterySensor(
                    coordinator,
                    entry,
                    "State of Charge",
                    "extendedData1",
                    "basicVehicleStatus",
                    SensorDeviceClass.BATTERY,
                    "%",
                    "mdi:battery",
                    "measurement",
                    1.0,
                ),
            )

        # Add all non-charging sensors first
        async_add_entities(sensors, update_before_add=True)

        # Now add the charging-related sensors, if charging data is available
        if "charging" in coordinator.data and coordinator.data["charging"]:
            charging_sensors = [
                SAICMGChargingSensor(
                    coordinator,
                    entry,
                    "Charging Voltage",
                    "bmsPackVol",
                    SensorDeviceClass.VOLTAGE,
                    "V",
                    "mdi:flash",
                    "measurement",
                    0.001,  # Convert from mV to V
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
                    0.001,  # Convert from mA to A
                    "chrgMgmtData",
                ),
                SAICMGChargingSensor(
                    coordinator,
                    entry,
                    "Target SOC",
                    "bmsOnBdChrgTrgtSOCDspCmd",
                    SensorDeviceClass.BATTERY,
                    "%",
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
                    "km",
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
                    "min",
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
                    "min",
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
                    "km",
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
                    "kWh",
                    "mdi:flash",
                    "measurement",
                    1.0,
                    "rvsChargeStatus",
                ),
                SAICMGChargingSensor(
                    coordinator,
                    entry,
                    "Mileage Since Last Charge",
                    "mileageSinceLastCharge",
                    SensorDeviceClass.DISTANCE,
                    "km",
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
            ]

            # Add charging sensors if they are available
            async_add_entities(charging_sensors, update_before_add=True)

    except Exception as e:
        LOGGER.error("Error setting up MG SAIC sensors: %s", e)


class SAICMGVehicleSensor(SensorEntity, RestoreEntity):
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
        self.coordinator = coordinator
        self._name = name
        self._field = field
        self._status_type = status_type
        self._device_class = device_class
        self._unit = unit
        self._state_class = state_class
        self._icon = icon
        self._state = None
        self._factor = factor
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = device_class
        vin_info = self.coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

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

    async def async_update(self):
        """Fetch new state data for the sensor."""
        try:
            status_data = getattr(
                self.coordinator.data["status"], self._status_type, None
            )
            if status_data:
                raw_value = getattr(status_data, self._field, None)
                if raw_value is not None:
                    self._state = raw_value * self._factor
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
            LOGGER.error("Error updating sensor %s: %s", self._name, e)


class SAICMGVehicleDetailSensor(SensorEntity, RestoreEntity):
    """Representation of a sensor for MG SAIC vehicle details."""

    def __init__(self, coordinator, entry, name, field):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._name = name
        self._field = field
        self._state = None
        vin_info = self.coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

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

    async def async_update(self):
        """Fetch new state data for the sensor."""
        try:
            vin_info = self.coordinator.data["info"][0]
            self._state = getattr(vin_info, self._field, None)
            self.async_write_ha_state()
        except Exception as e:
            LOGGER.error("Error updating vehicle detail sensor %s: %s", self._name, e)


class SAICMGChargingSensor(SensorEntity, RestoreEntity):
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
        factor,
        data_source="chrgMgmtData",
    ):
        """Initialize the sensor."""
        self.coordinator = coordinator
        self._name = name
        self._field = field
        self._device_class = device_class
        self._unit = unit
        self._state_class = state_class
        self._icon = icon
        self._state = None
        self._factor = factor
        self._data_source = data_source
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_device_class = device_class
        vin_info = self.coordinator.data["info"][0]
        self._unique_id = f"{entry.entry_id}_{vin_info.vin}_{field}_charge"

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def name(self):
        """Return the name of the sensor."""
        vin_info = self.coordinator.data["info"][0]
        return f"{vin_info.brandName} {vin_info.modelName} {self._name}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._state

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

    async def async_update(self):
        """Fetch new state data for the sensor."""
        try:
            charging_data = getattr(
                self.coordinator.data["charging"], self._data_source, None
            )
            raw_value = None  # Initialize raw_value to ensure it has a default value

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
                    if charging_status in [
                        0,
                        5,
                    ]:  # 0 = Not Charging, 5 = Charging Finished
                        self._state = 0  # Display 0 for these sensors when not charging
                    else:
                        raw_value = getattr(charging_data, self._field, None)
                        self._state = (
                            raw_value * self._factor if raw_value is not None else None
                        )

                elif self._field == "bmsOnBdChrgTrgtSOCDspCmd":
                    # Map the target SOC values to percentages
                    raw_value = getattr(charging_data, self._field, None)
                    self._state = {
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
                    self._state = {
                        0: "Not Charging",
                        1: "Charging (AC)",
                        5: "Charging Finished",
                    }.get(raw_value, f"Unknown ({raw_value})")

                else:
                    # Handle other numeric fields
                    raw_value = getattr(charging_data, self._field, None)
                    self._state = (
                        raw_value * self._factor if raw_value is not None else None
                    )

                if raw_value is None:
                    LOGGER.warning(
                        "Field %s returned None in charging data.", self._field
                    )
            else:
                LOGGER.error("No charging data available for %s", self._name)
                self._state = None

            self.async_write_ha_state()

        except Exception as e:
            LOGGER.error("Error updating charging sensor %s: %s", self._name, e)

    async def async_added_to_hass(self):
        """When entity is added to hass."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._state = last_state.state


class SAICMGBatterySensor(SAICMGVehicleSensor):
    """Specific sensor for battery state."""

    @property
    def device_class(self):
        """Return the class of this sensor."""
        return "battery"
