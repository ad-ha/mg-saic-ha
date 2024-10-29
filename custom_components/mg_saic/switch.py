from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, LOGGER


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
            ac_status = getattr(status.basicVehicleStatus, "remoteClimateStatus", None)
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
            seats_status = getattr(status.basicVehicleStatus, "heatedSeatsStatus", None)
            return seats_status == 1
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
            charging_status = getattr(charging_data, "chargingStatus", None)
            return charging_status == 1
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
