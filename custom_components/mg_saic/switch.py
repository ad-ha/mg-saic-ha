from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, LOGGER, CHARGING_STATUS_CODES


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MG SAIC switches."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]
    vin_info = coordinator.data["info"][0]
    vin = vin_info.vin

    switches = []

    # Extract vehicle configuration
    vehicle_config = {
        config.itemCode: config.itemValue
        for config in vin_info.vehicleModelConfiguration
    }

    # AC Switch
    switches.append(SAICMGACSwitch(coordinator, client, vin_info, vin))

    # Heated Seats Switch (if applicable)
    has_heated_seats = vehicle_config.get("HeatedSeat") == "1"

    if has_heated_seats:
        # Heated Seats Switch
        switches.append(SAICMGHeatedSeatsSwitch(coordinator, client, vin_info, vin))
    else:
        LOGGER.debug(
            f"Vehicle {vin} does not have heated seats. Skipping Heated Seats Switch."
        )

    # Charging Switch (for electric vehicles)
    if coordinator.vehicle_type in ["BEV", "PHEV"]:
        switches.append(SAICMGChargingSwitch(coordinator, client, vin_info, vin))

        # Check if battery heating is supported
        charging_data = coordinator.data.get("charging")
        if charging_data:
            chrgMgmtData = getattr(charging_data, "chrgMgmtData", None)
            if chrgMgmtData:
                bmsPTCHeatResp = getattr(chrgMgmtData, "bmsPTCHeatResp", None)
                if bmsPTCHeatResp is not None:
                    # Battery Heating Switch
                    switches.append(
                        SAICMGBatteryHeatingSwitch(coordinator, client, vin_info, vin)
                    )
                else:
                    LOGGER.debug(
                        f"Vehicle {vin} does not support battery heating. Skipping Battery Heating Switch."
                    )
            else:
                LOGGER.debug(
                    f"Charging management data not available for VIN {vin}. Cannot determine battery heating support."
                )
        else:
            LOGGER.debug(
                f"Charging data not available for VIN {vin}. Cannot determine battery heating support."
            )

    async_add_entities(switches)


class SAICMGVehicleSwitch(CoordinatorEntity, SwitchEntity):
    """Base class for MG SAIC switches."""

    def __init__(self, coordinator, client, vin_info, vin, name, icon):
        """Initialize the switch."""
        super().__init__(coordinator)
        self._client = client
        self._vin = vin
        self._vin_info = vin_info
        self._attr_name = f"{vin_info.brandName} {vin_info.modelName} {name}"
        self._attr_unique_id = f"{vin}_{name.replace(' ', '_').lower()}_switch"
        self._attr_icon = icon

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._vin)},
            "name": f"{self._vin_info.brandName} {self._vin_info.modelName}",
            "manufacturer": self._vin_info.brandName,
            "model": self._vin_info.modelName,
            "serial_number": self._vin,
        }

    async def async_turn_on(self, **kwargs):
        """Turn the switch on."""
        raise NotImplementedError()

    async def async_turn_off(self, **kwargs):
        """Turn the switch off."""
        raise NotImplementedError()

    @property
    def is_on(self):
        """Return true if the switch is on."""
        raise NotImplementedError()


class SAICMGACSwitch(SAICMGVehicleSwitch):
    """Switch to control the vehicle's AC."""

    def __init__(self, coordinator, client, vin_info, vin):
        super().__init__(
            coordinator,
            client,
            vin_info,
            vin,
            "Air Conditioning",
            "mdi:air-conditioner",
        )

    @property
    def is_on(self):
        """Return true if AC is on."""
        status = self.coordinator.data.get("status")
        if status:
            basic_status = getattr(status, "basicVehicleStatus", None)
            if basic_status:
                ac_status = getattr(basic_status, "remoteClimateStatus", None)
                return ac_status == 1
        return False

    async def async_turn_on(self, **kwargs):
        """Turn the AC on."""
        try:
            await self._client.start_ac(self._vin)
            LOGGER.info("AC started for VIN: %s", self._vin)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Error starting AC for VIN %s: %s", self._vin, e)

    async def async_turn_off(self, **kwargs):
        """Turn the AC off."""
        try:
            await self._client.stop_ac(self._vin)
            LOGGER.info("AC stopped for VIN: %s", self._vin)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Error stopping AC for VIN %s: %s", self._vin, e)


class SAICMGHeatedSeatsSwitch(SAICMGVehicleSwitch):
    """Switch to control the heated seats."""

    def __init__(self, coordinator, client, vin_info, vin):
        super().__init__(
            coordinator, client, vin_info, vin, "Heated Seats", "mdi:seat-recline-extra"
        )

    @property
    def is_on(self):
        """Return true if heated seats are on."""
        status = self.coordinator.data.get("status")
        if status:
            basic_status = getattr(status, "basicVehicleStatus", None)
            if basic_status:
                # Update is_on to check frontLeftSeatHeatLevel and frontRightSeatHeatLevel
                front_left_level = getattr(basic_status, "frontLeftSeatHeatLevel", 0)
                front_right_level = getattr(basic_status, "frontRightSeatHeatLevel", 0)
                return front_left_level > 0 or front_right_level > 0
        return False

    async def async_turn_on(self, **kwargs):
        """Turn the heated seats on."""
        try:
            await self._client.control_heated_seats(self._vin, True)
            LOGGER.info("Heated seats turned on for VIN: %s", self._vin)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Error turning on heated seats for VIN %s: %s", self._vin, e)

    async def async_turn_off(self, **kwargs):
        """Turn the heated seats off."""
        try:
            await self._client.control_heated_seats(self._vin, False)
            LOGGER.info("Heated seats turned off for VIN: %s", self._vin)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Error turning off heated seats for VIN %s: %s", self._vin, e)


class SAICMGChargingSwitch(SAICMGVehicleSwitch):
    """Switch to control vehicle charging."""

    def __init__(self, coordinator, client, vin_info, vin):
        super().__init__(
            coordinator, client, vin_info, vin, "Charging", "mdi:ev-station"
        )

    @property
    def is_on(self):
        """Return true if charging is active."""
        charging_data = self.coordinator.data.get("charging")
        if charging_data:
            chrgMgmtData = getattr(charging_data, "chrgMgmtData", None)
            if chrgMgmtData:
                charging_status = getattr(chrgMgmtData, "bmsChrgSts", None)
                return charging_status in CHARGING_STATUS_CODES
        return False

    async def async_turn_on(self, **kwargs):
        """Start charging."""
        try:
            await self._client.send_vehicle_charging_control(self._vin, "start")
            LOGGER.info("Charging started for VIN: %s", self._vin)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Error starting charging for VIN %s: %s", self._vin, e)

    async def async_turn_off(self, **kwargs):
        """Stop charging."""
        try:
            await self._client.send_vehicle_charging_control(self._vin, "stop")
            LOGGER.info("Charging stopped for VIN: %s", self._vin)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Error stopping charging for VIN %s: %s", self._vin, e)


class SAICMGBatteryHeatingSwitch(SAICMGVehicleSwitch):
    """Switch to control battery heating."""

    def __init__(self, coordinator, client, vin_info, vin):
        super().__init__(
            coordinator,
            client,
            vin_info,
            vin,
            "Battery Heating",
            "mdi:fire",
        )

    @property
    def is_on(self):
        """Return true if battery heating is active."""
        charging_data = self.coordinator.data.get("charging")
        if charging_data:
            chrgMgmtData = getattr(charging_data, "chrgMgmtData", None)
            if chrgMgmtData:
                bmsPTCHeatResp = getattr(chrgMgmtData, "bmsPTCHeatResp", None)
                return bmsPTCHeatResp == 1
        return False

    async def async_turn_on(self, **kwargs):
        """Start battery heating."""
        try:
            await self._client.send_vehicle_charging_ptc_heat(self._vin, "start")
            LOGGER.info("Battery heating started for VIN: %s", self._vin)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Error starting battery heating for VIN %s: %s", self._vin, e)

    async def async_turn_off(self, **kwargs):
        """Stop battery heating."""
        try:
            await self._client.send_vehicle_charging_ptc_heat(self._vin, "stop")
            LOGGER.info("Battery heating stopped for VIN: %s", self._vin)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Error stopping battery heating for VIN %s: %s", self._vin, e)
