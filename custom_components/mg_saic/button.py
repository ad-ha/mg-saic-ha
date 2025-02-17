# File: button.py

import asyncio
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    LOGGER,
)
from .utils import create_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MG SAIC buttons."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]

    if not coordinator.data.get("info"):
        LOGGER.error("Vehicle info is not available. Buttons cannot be set up.")
        return

    vin_info = coordinator.vin_info
    vin = vin_info.vin

    buttons = [
        SAICMGTriggerAlarmButton(coordinator, client, entry, vin_info, vin),
        SAICMGUpdateDataButton(coordinator, client, entry, vin_info, vin),
    ]

    async_add_entities(buttons)


class SAICMGButton(CoordinatorEntity, ButtonEntity):
    """Base class for MG SAIC buttons."""

    def __init__(self, coordinator, client, entry, vin_info, vin, name, icon):
        """Initialize the button."""
        super().__init__(coordinator)
        self._client = client
        self._vin = vin
        self._vin_info = vin_info
        self._attr_name = f"{vin_info.brandName} {vin_info.modelName} {name}"
        self._attr_unique_id = (
            f"{entry.entry_id}_{vin}_{name.replace(' ', '_').lower()}_button"
        )
        self._attr_icon = icon

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def device_info(self):
        """Return device info"""
        return self._device_info

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


class SAICMGTriggerAlarmButton(CoordinatorEntity, ButtonEntity):
    """Button to trigger the vehicle alarm."""

    def __init__(self, coordinator, client, entry, vin_info, vin):
        """Initialize the alarm trigger button."""
        super().__init__(coordinator)
        self._client = client
        self._vin = vin
        self._vin_info = vin_info
        self._attr_name = f"{vin_info.brandName} {vin_info.modelName} Trigger Alarm"
        self._attr_unique_id = f"{entry.entry_id}_{vin}_trigger_alarm_button"
        self._attr_icon = "mdi:alarm-light"
        self._device_info = create_device_info(coordinator, entry.entry_id)

    async def async_press(self):
        """Handle the button press."""
        try:
            immediate_interval = self.coordinator.after_action_delay
            long_interval = self.coordinator.alarm_long_interval

            await self._client.trigger_alarm(self._vin)
            LOGGER.info("Alarm triggered for VIN: %s", self._vin)
            await self.coordinator.schedule_action_refresh(
                self._vin,
                immediate_interval,
                long_interval,
            )
        except Exception as e:
            LOGGER.error("Error triggering alarm for VIN %s: %s", self._vin, e)

    @property
    def device_info(self):
        """Return device info"""
        return self._device_info


class SAICMGUpdateDataButton(CoordinatorEntity, ButtonEntity):
    """Button to manually update vehicle data."""

    def __init__(self, coordinator, client, entry, vin_info, vin):
        """Initialize the update data button."""
        super().__init__(coordinator)
        self._client = client
        self._vin = vin
        self._vin_info = vin_info
        self._attr_name = (
            f"{vin_info.brandName} {vin_info.modelName} Update Vehicle Data"
        )
        self._attr_unique_id = f"{entry.entry_id}_{vin}_update_vehicle_data_button"
        self._attr_icon = "mdi:update"
        self._device_info = create_device_info(coordinator, entry.entry_id)

    async def async_press(self):
        """Handle the button press."""
        try:
            await self.coordinator.async_request_refresh()
            LOGGER.info("Data update triggered for VIN: %s", self._vin)
        except Exception as e:
            LOGGER.error("Error triggering data update for VIN %s: %s", self._vin, e)

    @property
    def device_info(self):
        """Return device info"""
        return self._device_info
