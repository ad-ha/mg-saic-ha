from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import PERCENTAGE
from .const import DOMAIN, LOGGER


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MG SAIC number entities."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]
    vin_info = coordinator.data["info"][0]
    vin = vin_info.vin

    number_entities = []

    # Check if the vehicle supports setting Target SOC
    vehicle_type = coordinator.vehicle_type
    if vehicle_type in ["BEV", "PHEV"]:
        number_entities.append(
            SAICMGTargetSOCNumber(coordinator, client, vin_info, vin)
        )

    async_add_entities(number_entities)


class SAICMGTargetSOCNumber(CoordinatorEntity, NumberEntity):
    """Representation of a Target SOC number entity."""

    def __init__(self, coordinator, client, vin_info, vin):
        """Initialize the Target SOC number entity."""
        super().__init__(coordinator)
        self._client = client
        self._vin = vin
        self._vin_info = vin_info

        self._attr_name = f"{vin_info.brandName} {vin_info.modelName} Target SOC"
        self._attr_unique_id = f"{vin}_target_soc"
        self._attr_native_min_value = 40
        self._attr_native_max_value = 100
        self._attr_native_step = 10
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_mode = NumberMode.SLIDER

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
    def native_value(self):
        """Return the current target SOC value."""
        charging_data = self.coordinator.data.get("charging")
        if charging_data:
            chrg_mgmt_data = getattr(charging_data, "chrgMgmtData", None)
            if chrg_mgmt_data:
                soc_cmd = getattr(chrg_mgmt_data, "bmsOnBdChrgTrgtSOCDspCmd", None)
                # Map the SOC command to percentage
                soc_mapping = {
                    1: 40,
                    2: 50,
                    3: 60,
                    4: 70,
                    5: 80,
                    6: 90,
                    7: 100,
                }
                return soc_mapping.get(soc_cmd)
        return None

    @property
    def icon(self):
        """Return the icon based on the current SOC value."""
        if self.native_value >= 100:
            return "mdi:battery-charging-100"
        elif self.native_value >= 90:
            return "mdi:battery-charging-90"
        elif self.native_value >= 80:
            return "mdi:battery-charging-80"
        elif self.native_value >= 70:
            return "mdi:battery-charging-70"
        elif self.native_value >= 60:
            return "mdi:battery-charging-60"
        elif self.native_value >= 50:
            return "mdi:battery-charging-50"
        elif self.native_value >= 40:
            return "mdi:battery-charging-40"
        else:
            return "mdi:battery-charging-outline"

    async def async_set_native_value(self, value: float) -> None:
        """Set the target SOC to the specified value."""
        target_soc = int(value)
        try:
            await self._client.set_target_soc(self._vin, target_soc)
            LOGGER.info("Set Target SOC to %d%% for VIN: %s", target_soc, self._vin)
            # Schedule data refresh
            await self.coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Error setting Target SOC for VIN %s: %s", self._vin, e)