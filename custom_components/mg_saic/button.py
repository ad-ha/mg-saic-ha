from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, LOGGER
import asyncio


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MG SAIC buttons."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]

    if not coordinator.data.get("info"):
        LOGGER.error("Vehicle info is not available. Buttons cannot be set up.")
        return

    vin_info = coordinator.data["info"][0]
    vin = vin_info.vin

    buttons = [
        SAICMGTriggerAlarmButton(coordinator, client, vin_info, vin),
        SAICMGUpdateDataButton(coordinator, client, vin_info, vin),
    ]

    async_add_entities(buttons)


class SAICMGButton(CoordinatorEntity, ButtonEntity):
    """Base class for MG SAIC buttons."""

    def __init__(self, coordinator, client, vin_info, vin, name, icon):
        """Initialize the button."""
        super().__init__(coordinator)
        self._client = client
        self._vin = vin
        self._vin_info = vin_info
        self._attr_name = f"{vin_info.brandName} {vin_info.modelName} {name}"
        self._attr_unique_id = f"{vin}_{name.replace(' ', '_').lower()}_button"
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

    async def schedule_data_refresh(self):
        """Schedule a data refresh for the coordinator associated with the VIN."""
        coordinators_by_vin = self.hass.data[DOMAIN].get("coordinators_by_vin", {})
        coordinator = coordinators_by_vin.get(self._vin)
        if coordinator:

            async def delayed_refresh():
                await asyncio.sleep(15)  # Wait for 15 seconds
                await coordinator.async_request_refresh()

            self.hass.async_create_task(delayed_refresh())
        else:
            LOGGER.warning("Coordinator not found for VIN %s", self._vin)


class SAICMGTriggerAlarmButton(SAICMGButton):
    """Button to trigger the vehicle alarm."""

    def __init__(self, coordinator, client, vin_info, vin):
        super().__init__(
            coordinator, client, vin_info, vin, "Trigger Alarm", "mdi:alarm-light"
        )

    async def async_press(self):
        """Handle the button press."""
        try:
            await self._client.trigger_alarm(self._vin)
            LOGGER.info("Alarm triggered for VIN: %s", self._vin)
            await self.schedule_data_refresh()
        except Exception as e:
            LOGGER.error("Error triggering alarm for VIN %s: %s", self._vin, e)


class SAICMGUpdateDataButton(SAICMGButton):
    """Button to manually update vehicle data."""

    def __init__(self, coordinator, client, vin_info, vin):
        super().__init__(
            coordinator, client, vin_info, vin, "Update Vehicle Data", "mdi:update"
        )

    async def async_press(self):
        """Handle the button press."""
        try:
            await self.coordinator.async_request_refresh()
            LOGGER.info("Data update triggered for VIN: %s", self._vin)
        except Exception as e:
            LOGGER.error("Error triggering data update for VIN %s: %s", self._vin, e)
