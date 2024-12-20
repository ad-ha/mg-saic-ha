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
from .const import (
    DOMAIN,
    LOGGER,
)
from .utils import create_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the MG SAIC climate entity."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]

    if not coordinator.data.get("info"):
        LOGGER.error("Vehicle info is not available. Climate cannot be set up.")
        return

    vin_info = coordinator.data["info"][0]
    vin = vin_info.vin

    climate_entity = SAICMGClimateEntity(coordinator, client, entry, vin_info, vin)
    async_add_entities([climate_entity])


class SAICMGClimateEntity(CoordinatorEntity, ClimateEntity):
    """Representation of the vehicle's climate control."""

    def __init__(self, coordinator, client, entry, vin_info, vin):
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
        self._attr_hvac_modes = [
            HVACMode.OFF,
            HVACMode.COOL,
            HVACMode.FAN_ONLY,
        ]
        self._attr_fan_modes = [FAN_LOW, FAN_MEDIUM, FAN_HIGH]

        self._device_info = create_device_info(coordinator, entry.entry_id)

        # Initialize with default values
        self._attr_current_temperature = None
        self._attr_target_temperature = 22.0
        self._attr_fan_mode = FAN_MEDIUM
        self._attr_hvac_mode = HVACMode.OFF

    @property
    def target_temperature_step(self):
        """Return the step size for target temperature."""
        return 1.0

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
            elif ac_status == 2:
                return HVACMode.FAN_ONLY
        return HVACMode.OFF

    async def async_set_hvac_mode(self, hvac_mode):
        """Set the HVAC mode."""
        try:
            if hvac_mode == HVACMode.OFF:
                await self._client.stop_ac(self._vin)
            elif hvac_mode == HVACMode.COOL:
                await self._client.start_climate(
                    self._vin,
                    self._attr_target_temperature,
                    self._fan_speed_to_int(),
                    ac_on=True,
                )
            elif hvac_mode == HVACMode.FAN_ONLY:
                await self._client.start_climate(
                    self._vin,
                    self._attr_target_temperature,
                    self._fan_speed_to_int(),
                    ac_on=False,
                )
            else:
                LOGGER.warning("Unsupported HVAC mode: %s", hvac_mode)
                return

            self._attr_hvac_mode = hvac_mode

            # Schedule data refresh
            immediate_interval = self.coordinator.after_action_delay
            long_interval = self.coordinator.ac_long_interval

            await self.coordinator.schedule_action_refresh(
                self._vin,
                immediate_interval,
                long_interval,
            )

        except Exception as e:
            LOGGER.error("Error setting HVAC mode for VIN %s: %s", self._vin, e)

    async def async_turn_on(self):
        """Turn the climate entity on."""
        immediate_interval = self.coordinator.after_action_delay
        long_interval = self.coordinator.ac_long_interval

        await self.async_set_hvac_mode(HVACMode.COOL)
        await self.coordinator.schedule_action_refresh(
            self._vin,
            immediate_interval,
            long_interval,
        )

    async def async_turn_off(self):
        """Turn the climate entity off."""
        immediate_interval = self.coordinator.after_action_delay
        long_interval = self.coordinator.ac_long_interval

        await self.async_set_hvac_mode(HVACMode.OFF)
        await self.coordinator.schedule_action_refresh(
            self._vin,
            immediate_interval,
            long_interval,
        )

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        immediate_interval = self.coordinator.after_action_delay
        long_interval = self.coordinator.ac_long_interval

        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            self._attr_target_temperature = temperature
            if self.hvac_mode != HVACMode.OFF:
                await self._client.start_climate(
                    self._vin, temperature, self._fan_speed_to_int(), ac_on=True
                )
                # Schedule data refresh
                await self.coordinator.schedule_action_refresh(
                    self._vin,
                    immediate_interval,
                    long_interval,
                )

    @property
    def fan_mode(self):
        """Return the current fan mode."""
        return self._attr_fan_mode

    async def async_set_fan_mode(self, fan_mode):
        """Set the fan mode."""
        immediate_interval = self.coordinator.after_action_delay
        long_interval = self.coordinator.ac_long_interval

        if fan_mode in self._attr_fan_modes:
            self._attr_fan_mode = fan_mode
            if self.hvac_mode != HVACMode.OFF:
                await self._client.start_climate(
                    self._vin,
                    self._attr_target_temperature,
                    self._fan_speed_to_int(),
                    ac_on=True,
                )
                # Schedule data refresh
                await self.coordinator.schedule_action_refresh(
                    self._vin,
                    immediate_interval,
                    long_interval,
                )
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

    @property
    def device_info(self):
        """Return device info"""
        return self._device_info
