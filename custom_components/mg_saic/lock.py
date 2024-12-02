from homeassistant.components.lock import LockEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, LOGGER


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MG SAIC lock entity."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]

    if not coordinator.data.get("info"):
        LOGGER.error("Vehicle info is not available. Lock cannot be set up.")
        return

    vin_info = coordinator.data["info"][0]
    vin = vin_info.vin

    lock_entities = [
        SAICMGLockEntity(coordinator, client, vin_info, vin),
        SAICMGBootLockEntity(coordinator, client, vin_info, vin),
    ]

    async_add_entities(lock_entities)


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
            return lock_status == 1
        return None

    @property
    def available(self):
        """Return True if the lock entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get("status") is not None
        )

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


class SAICMGBootLockEntity(CoordinatorEntity, LockEntity):
    """Representation of the vehicle's boot as a lock."""

    def __init__(self, coordinator, client, vin_info, vin):
        """Initialize the boot lock entity."""
        super().__init__(coordinator)
        self._client = client
        self._vin = vin
        self._vin_info = vin_info

        self._attr_name = f"{vin_info.brandName} {vin_info.modelName} Boot"
        self._attr_unique_id = f"{vin}_boot_lock"
        self._attr_icon = "mdi:car-back"

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
        """Return true if the boot is closed (locked)."""
        status = self.coordinator.data.get("status")
        if status:
            boot_status = getattr(status.basicVehicleStatus, "bootStatus", None)
            return boot_status == 0
        return None

    @property
    def available(self):
        """Return True if the lock entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get("status") is not None
        )

    async def async_lock(self, **kwargs):
        """Lock (close) the boot."""
        # Since we can only open the boot, we log that closing is manual
        LOGGER.warning("Closing the boot must be done manually.")

    async def async_unlock(self, **kwargs):
        """Unlock (open) the boot."""
        try:
            await self._client.open_tailgate(self._vin)
            LOGGER.info("Boot opened for VIN: %s", self._vin)
            await self.coordinator.async_request_refresh()
        except Exception as e:
            LOGGER.error("Error opening boot for VIN %s: %s", self._vin, e)
