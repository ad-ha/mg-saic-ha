from homeassistant.components.lock import LockEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, LOGGER


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MG SAIC lock entity."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]
    vin_info = coordinator.data["info"][0]
    vin = vin_info.vin

    lock_entity = SAICMGLockEntity(coordinator, client, vin_info, vin)
    async_add_entities([lock_entity])


class SAICMGLockEntity(CoordinatorEntity, LockEntity):
    """Representation of the vehicle's lock."""

    def __init__(self, coordinator, client, vin_info, vin):
        """Initialize the lock entity."""
        super().__init__(coordinator)
        self._client = client
        self._vin = vin
        self._vin_info = vin_info

        self._attr_name = f"{vin_info.brandName} {vin_info.modelName} Lock"
        self._attr_unique_id = f"{vin}_lock"

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
    def is_locked(self):
        """Return true if the vehicle is locked."""
        status = self.coordinator.data.get("status")
        if status:
            lock_status = getattr(status.basicVehicleStatus, "lockStatus", None)
            return lock_status == 1  # Assuming 1 means locked
        return None

    async def async_lock(self, **kwargs):
        """Lock the vehicle."""
        try:
            await self._client.lock_vehicle(self._vin)
            LOGGER.info("Vehicle locked for VIN: %s", self._vin)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Error locking vehicle for VIN %s: %s", self._vin, e)

    async def async_unlock(self, **kwargs):
        """Unlock the vehicle."""
        try:
            await self._client.unlock_vehicle(self._vin)
            LOGGER.info("Vehicle unlocked for VIN: %s", self._vin)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Error unlocking vehicle for VIN %s: %s", self._vin, e)
