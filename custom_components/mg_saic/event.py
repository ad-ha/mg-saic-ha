# File: event.py

from homeassistant.components.event import EventEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, LOGGER
from .utils import create_device_info

# Event types this entity can fire. Only types listed here may be triggered —
# attempting to fire any other type raises a ValueError (HA core enforces
# this in EventEntity._trigger_event).
EVENT_TYPE_COMMAND_ERROR = "command_error"
EVENT_TYPE_COMMAND_LIMIT_REACHED = "command_limit_reached"

EVENT_TYPES = [
    EVENT_TYPE_COMMAND_ERROR,
    EVENT_TYPE_COMMAND_LIMIT_REACHED,
]


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the MG SAIC command error event entity."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]

    if not coordinator.data.get("info"):
        LOGGER.error("Vehicle info is not available. Event entity cannot be set up.")
        return

    vin_info = coordinator.vin_info
    vin = vin_info.vin

    async_add_entities(
        [SAICMGCommandErrorEvent(coordinator, client, entry, vin_info, vin)]
    )


class SAICMGCommandErrorEvent(CoordinatorEntity, EventEntity):
    """Event entity that surfaces remote command failures in the HA Logbook.

    This is a passive, fire-and-forget complement to the persistent
    notification raised for CommandsLimitReachedException: the notification
    is for "needs user action now", while this event entity gives a
    queryable history of every command failure (including, but not limited
    to, command-limit-reached events) for later review in the Logbook or in
    automations.

    The coordinator calls record_command_error()/record_command_limit_reached()
    on this entity directly; entities themselves don't need to know about
    this platform.
    """

    _attr_should_poll = False

    def __init__(self, coordinator, client, entry, vin_info, vin):
        """Initialize the command error event entity."""
        super().__init__(coordinator)
        self._client = client
        self._vin = vin
        self._vin_info = vin_info
        self._attr_name = f"{vin_info.brandName} {vin_info.modelName} Command Errors"
        self._attr_unique_id = f"{entry.entry_id}_{vin}_command_errors_event"
        self._attr_icon = "mdi:alert-circle-outline"
        self._attr_event_types = EVENT_TYPES
        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def device_info(self):
        """Return device info."""
        return self._device_info

    @property
    def available(self):
        """This entity is always available — it has no dependency on the
        latest coordinator poll succeeding, since it only reflects command
        outcomes, not vehicle telemetry."""
        return True

    async def async_added_to_hass(self):
        """Register this entity with the coordinator once added to HA."""
        await super().async_added_to_hass()
        self.coordinator.register_command_error_event_entity(self)

    async def async_will_remove_from_hass(self):
        """Deregister from the coordinator when removed."""
        self.coordinator.register_command_error_event_entity(None)
        await super().async_will_remove_from_hass()

    def record_command_error(self, source: str, error: str) -> None:
        """Fire a generic command_error event.

        Args:
            source: short identifier of what failed, e.g. "climate.set_hvac_mode"
            error: the error message/exception string
        """
        self._trigger_event(
            EVENT_TYPE_COMMAND_ERROR,
            {"source": source, "error": error},
        )
        self.async_write_ha_state()

    def record_command_limit_reached(self, source: str) -> None:
        """Fire a command_limit_reached event.

        Args:
            source: short identifier of which command triggered the limit,
                e.g. "climate.set_hvac_mode"
        """
        self._trigger_event(
            EVENT_TYPE_COMMAND_LIMIT_REACHED,
            {
                "source": source,
                "message": (
                    "Vehicle reached the maximum number of remote commands. "
                    "Start the vehicle with the physical key to reset."
                ),
            },
        )
        self.async_write_ha_state()
