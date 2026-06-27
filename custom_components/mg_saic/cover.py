# File: cover.py
"""Cover platform for MG SAIC — exposes the vehicle boot state as a read-only
cover entity.

The boot status (open/closed) is shown here so that automations and dashboards
can react to it (e.g. alert if left open). The *action* to open the boot is
handled by SAICMGOpenBootButton in button.py, which is always pressable
regardless of current state — matching the SAIC API's one-shot latch-release
behaviour.

This separation avoids the awkward cover UX where HA disables the Open arrow
when the boot is already open, and prevents a spurious Close button appearing.
A cover entity with no supported_features is the HA-idiomatic way to expose
a state-only cover.

Migration note: this entity's unique_id is intentionally distinct from the
old SAICMGBootLockEntity (``<entry_id>_<vin>_boot_lock`` on the lock platform).
HA will create this as a new entity (``cover.<brand>_<model>_boot``) on first
load. The old lock entity (``lock.<brand>_<model>_boot``) will appear as
orphaned in the entity registry and can be safely removed via the HA UI.
"""

from homeassistant.components.cover import CoverDeviceClass, CoverEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    LOGGER,
)
from .utils import create_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MG SAIC cover entities."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]

    if not coordinator.data.get("info"):
        LOGGER.error("Vehicle info is not available. Cover cannot be set up.")
        return

    vin_info = coordinator.vin_info
    vin = vin_info.vin

    async_add_entities(
        [SAICMGBootCoverEntity(coordinator, entry, vin_info, vin)]
    )


class SAICMGBootCoverEntity(CoordinatorEntity, CoverEntity):
    """Read-only cover entity reflecting the vehicle boot open/closed state.

    No supported_features are declared, so HA renders no action buttons —
    the entity is purely a state sensor in cover form. The Open Boot button
    entity (button platform) handles the actual latch-release action.
    """

    _attr_device_class = CoverDeviceClass.GARAGE
    _attr_icon = "mdi:car-back"
    # No _attr_supported_features — defaults to 0 (no Open/Close buttons)

    def __init__(self, coordinator, entry, vin_info, vin):
        """Initialise the boot status cover entity."""
        super().__init__(coordinator)
        self._vin = vin
        self._vin_info = vin_info

        self._attr_name = f"{vin_info.brandName} {vin_info.modelName} Boot"
        self._attr_unique_id = f"{entry.entry_id}_{vin}_boot_cover"

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info

    @property
    def is_closed(self) -> bool | None:
        """Return True when the boot is closed (bootStatus == 0)."""
        status = self.coordinator.data.get("status")
        if status:
            boot_status = getattr(status.basicVehicleStatus, "bootStatus", None)
            if boot_status is not None:
                return boot_status == 0
        return None

    @property
    def available(self) -> bool:
        """Return True if status data is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get("status") is not None
        )
