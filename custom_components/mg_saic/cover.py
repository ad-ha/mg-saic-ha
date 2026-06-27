# File: cover.py
"""Cover platform for MG SAIC — exposes the vehicle boot as a cover entity.

Using HA's cover platform (rather than the lock platform previously used)
gives the correct "Open" / "Close" action labels in the UI, matching the
boot status sensor which already shows "Open" / "Closed".

Migration note: this entity's unique_id is intentionally distinct from the
old SAICMGBootLockEntity (which used unique_id ``<entry_id>_<vin>_boot_lock``
on the lock platform).  HA will create this as a new entity
(``cover.<brand>_<model>_boot``) on first load.  The old lock entity
(``lock.<brand>_<model>_boot``) will appear as orphaned in the entity
registry and can be safely removed via the HA UI or entity registry.
"""

from homeassistant.components.cover import CoverDeviceClass, CoverEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import CommandsLimitReachedException
from .const import (
    DOMAIN,
    LOGGER,
)
from .utils import create_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MG SAIC cover entities."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]

    if not coordinator.data.get("info"):
        LOGGER.error("Vehicle info is not available. Cover cannot be set up.")
        return

    vin_info = coordinator.vin_info
    vin = vin_info.vin

    async_add_entities(
        [SAICMGBootCoverEntity(coordinator, client, entry, vin_info, vin)]
    )


class SAICMGBootCoverEntity(CoordinatorEntity, CoverEntity):
    """Representation of the vehicle boot as a cover (open/close).

    The SAIC API only supports *opening* the boot remotely — closing must be
    done manually (physically closing the lid). The entity reflects the real
    boot state via ``bootStatus`` from vehicle status data.

    Device class ``trunk`` gives the correct icon and Open/Close labels in
    the HA UI and Lovelace cards.
    """

    _attr_device_class = CoverDeviceClass.GARAGE  # closest generic "open lid"
    _attr_icon = "mdi:car-back"

    def __init__(self, coordinator, client, entry, vin_info, vin):
        """Initialise the boot cover entity."""
        super().__init__(coordinator)
        self._client = client
        self._vin = vin
        self._vin_info = vin_info

        self._attr_name = f"{vin_info.brandName} {vin_info.modelName} Boot"
        # New unique_id on the cover platform — distinct from the old lock entity.
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

    async def async_open_cover(self, **kwargs) -> None:
        """Open the boot (release the latch remotely)."""
        try:
            immediate_interval = self.coordinator.after_action_delay
            long_interval = self.coordinator.tailgate_long_interval

            await self._client.open_tailgate(self._vin)
            LOGGER.info("Boot opened for VIN: %s", self._vin)
            await self.coordinator.schedule_action_refresh(
                self._vin,
                immediate_interval,
                long_interval,
            )
        except CommandsLimitReachedException:
            await self.coordinator.notify_command_limit_reached(self._vin)
        except Exception as e:
            LOGGER.error("Error opening boot for VIN %s: %s", self._vin, e)
            self.coordinator.record_command_error("Error opening boot", e)

    async def async_close_cover(self, **kwargs) -> None:
        """Close cover — not supported remotely; boot must be closed manually."""
        LOGGER.warning(
            "Remote boot close is not supported by the SAIC API for VIN %s. "
            "Please close the boot manually.",
            self._vin,
        )
