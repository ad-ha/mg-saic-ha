from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.climate.const import (
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
)
from homeassistant.const import (
    UnitOfTemperature,
    ATTR_TEMPERATURE,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, LOGGER


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the MG SAIC climate entity."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]

    if not coordinator.data.get("info"):
        LOGGER.error("Vehicle info is not available. Climate cannot be set up.")
        return

    vin_info = coordinator.data["info"][0]
    vin = vin_info.vin

    climate_entity = SAICMGClimateEntity(coordinator, client, vin_info, vin)
    async_add_entities([climate_entity])


class SAICMGClimateEntity(CoordinatorEntity, ClimateEntity):
    """Representation of the vehicle's climate control."""

    def __init__(self, coordinator, client, vin_info, vin):
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._client = client
        self._vin = vin
        self._vin_info = vin_info

        self._attr_name = f"{vin_info.brandName} {vin_info.modelName} Climate"
        self._attr_unique_id = f"{vin}_climate"
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL]
        self._attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH]

        # Initialize with default values
        self._attr_current_temperature = None
        self._attr_target_temperature = 22.0
        self._attr_fan_mode = FAN_MEDIUM
        self._attr_hvac_mode = HVACMode.OFF

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

    @property
    def current_temperature(self):
        """Return the current interior temperature."""
        status = self.coordinator.data.get("status")
        if status:
            interior_temp = getattr(
                status.basicVehicleStatus, "interiorTemperature", None
            )
            if interior_temp is not None and interior_temp != -128:
                return interior_temp
        return None

    @property
    def hvac_mode(self):
        """Return the current HVAC mode."""
        status = self.coordinator.data.get("status")
        if status:
            ac_status = getattr(status.basicVehicleStatus, "remoteClimateStatus", None)
            if ac_status == 3:
                return HVACMode.COOL
        return HVACMode.OFF

    async def async_set_hvac_mode(self, hvac_mode):
        """Set the HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self._client.stop_ac(self._vin)
            self._attr_hvac_mode = HVACMode.OFF
        elif hvac_mode == HVACMode.COOL:
            await self._client.start_climate(
                self._vin, self._attr_target_temperature, self._fan_speed_to_int()
            )
            self._attr_hvac_mode = HVACMode.COOL
        else:
            LOGGER.warning("Unsupported HVAC mode: %s", hvac_mode)
            return
        # Schedule data refresh
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self):
        """Turn the climate entity on."""
        await self.async_set_hvac_mode(HVACMode.COOL)

    async def async_turn_off(self):
        """Turn the climate entity off."""
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._attr_target_temperature = temperature
            if self.hvac_mode != HVACMode.OFF:
                await self._client.start_climate(
                    self._vin, temperature, self._fan_speed_to_int()
                )
                # Schedule data refresh
                await self.coordinator.async_request_refresh()

    @property
    def fan_mode(self):
        """Return the current fan mode."""
        return self._attr_fan_mode

    async def async_set_fan_mode(self, fan_mode):
        """Set the fan mode."""
        if fan_mode in self._attr_fan_modes:
            self._attr_fan_mode = fan_mode
            if self.hvac_mode != HVACMode.OFF:
                await self._client.start_climate(
                    self._vin, self._attr_target_temperature, self._fan_speed_to_int()
                )
                # Schedule data refresh
                await self.coordinator.async_request_refresh()
        else:
            LOGGER.warning("Unsupported fan mode: %s", fan_mode)

    @property
    def available(self):
        """Return True if the climate entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get("status") is not None
        )

    def _fan_speed_to_int(self):
        """Convert fan mode to integer value expected by the API."""
        mapping = {
            FAN_LOW: 1,
            FAN_MEDIUM: 3,
            FAN_HIGH: 5,
        }
        fan_speed = mapping.get(self._attr_fan_mode)
        if fan_speed is None:
            raise ValueError("Invalid fan mode.")
        return fan_speed

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return 16.0

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return 30.0
