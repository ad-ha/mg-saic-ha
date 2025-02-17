# File: select.py

from homeassistant.components.select import SelectEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import (
    DOMAIN,
    LOGGER,
    ChargeCurrentLimitOption,
    BatterySoc,
)
from saic_ismart_client_ng.api.vehicle_charging import (
    ChargeCurrentLimitCode as ExternalChargeCurrentLimitCode,
)
from .utils import create_device_info


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up MG SAIC select entities."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]
    client = hass.data[DOMAIN][entry.entry_id]

    if not coordinator.data.get("info"):
        LOGGER.error("Vehicle info is not available. Select entities cannot be set up.")
        return

    vin_info = coordinator.vin_info
    vin = vin_info.vin

    select_entities = [
        SAICMGChargingCurrentSelect(
            coordinator, client, entry, vin_info, vin, "mdi:current-ac"
        ),
    ]

    if coordinator.has_heated_seats:
        select_entities.extend(
            [
                SAICMGHeatedSeatLevelSelect(
                    coordinator,
                    client,
                    entry,
                    vin_info,
                    vin,
                    "Front Left",
                    "frontLeft",
                    "mdi:car-seat-heater",
                ),
                SAICMGHeatedSeatLevelSelect(
                    coordinator,
                    client,
                    entry,
                    vin_info,
                    vin,
                    "Front Right",
                    "frontRight",
                    "mdi:car-seat-heater",
                ),
            ]
        )

    async_add_entities(select_entities)


class SAICMGChargingCurrentSelect(CoordinatorEntity, SelectEntity):
    """Representation of a Charging Current Limit select entity."""

    def __init__(self, coordinator, client, entry, vin_info, vin, icon):
        """Initialize the Charging Current Limit select entity."""
        super().__init__(coordinator)
        self._client = client
        self._vin = vin
        self._vin_info = vin_info
        self._icon = icon

        self._attr_name = (
            f"{vin_info.brandName} {vin_info.modelName} Charging Current Limit"
        )
        self._attr_unique_id = f"{entry.entry_id}_{vin}_charging_current_limit"
        self._attr_options = [e.limit for e in ChargeCurrentLimitOption]

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def device_info(self):
        """Return device info"""
        return self._device_info

    @property
    def current_option(self):
        """Return the current selected option."""
        charging_data = self.coordinator.data.get("charging")
        if charging_data:
            chrg_mgmt_data = getattr(charging_data, "chrgMgmtData", None)
            if chrg_mgmt_data:
                current_limit_code_value = getattr(
                    chrg_mgmt_data, "bmsAltngChrgCrntDspCmd", None
                )
                if current_limit_code_value is not None:
                    try:
                        external_code = ExternalChargeCurrentLimitCode(
                            current_limit_code_value
                        )
                        for option in ChargeCurrentLimitOption:
                            if option.value == external_code.value:
                                return option.limit
                    except ValueError:
                        LOGGER.error(
                            f"Unknown external charge current limit code: {current_limit_code_value}"
                        )
                        return None
        return None

    @property
    def available(self):
        """Return True if the entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data.get("charging") is not None
        )

    async def async_select_option(self, option: str):
        """Set the Charging Current Limit to the selected option."""
        try:
            # Map the string option to the local enum
            selected_code = ChargeCurrentLimitOption.to_code(option)

            # Get the current target_soc from coordinator's data
            charging_data = self.coordinator.data.get("charging")
            if not charging_data:
                LOGGER.error(
                    "No charging data available to set charging current limit."
                )
                return

            chrg_mgmt_data = getattr(charging_data, "chrgMgmtData", None)
            if not chrg_mgmt_data:
                LOGGER.error(
                    "No charging management data available to set charging current limit."
                )
                return

            target_soc_value = getattr(chrg_mgmt_data, "bmsOnBdChrgTrgtSOCDspCmd", None)
            if target_soc_value is None:
                LOGGER.error(
                    "Target SOC value is not available to set charging current limit."
                )
                return

            # Map the target_soc_value to BatterySoc enum
            target_soc_enum = {
                1: BatterySoc.SOC_40,
                2: BatterySoc.SOC_50,
                3: BatterySoc.SOC_60,
                4: BatterySoc.SOC_70,
                5: BatterySoc.SOC_80,
                6: BatterySoc.SOC_90,
                7: BatterySoc.SOC_100,
            }.get(target_soc_value, None)

            if target_soc_enum is None:
                LOGGER.error(f"Unknown target SOC value: {target_soc_value}")
                raise ValueError(f"Unknown target SOC value: {target_soc_value}")

            # Set the charging current limit with target_soc
            await self._client.set_current_limit(
                self._vin, target_soc_enum, selected_code
            )
            LOGGER.info(
                "Set Charging Current Limit to %s for VIN: %s", option, self._vin
            )
            # Schedule a refresh
            immediate_interval = self.coordinator.after_action_delay
            long_interval = self.coordinator.charging_current_long_interval

            await self.coordinator.schedule_action_refresh(
                self._vin,
                immediate_interval,
                long_interval,
            )
        except ValueError as e:
            LOGGER.error("Invalid option selected: %s", option)
            raise
        except Exception as e:
            LOGGER.error(
                "Error setting Charging Current Limit to %s for VIN %s: %s",
                option,
                self._vin,
                e,
            )


class SAICMGHeatedSeatLevelSelect(CoordinatorEntity, SelectEntity):
    """Select entity to control heating levels for heated seats."""

    def __init__(
        self, coordinator, client, entry, vin_info, vin, seat_name, seat_id, icon
    ):
        super().__init__(coordinator)
        self._client = client
        self._vin = vin
        self._vin_info = vin_info
        self._seat_id = seat_id
        self._icon = icon
        self._attr_name = (
            f"{vin_info.brandName} {vin_info.modelName} Heated Seat {seat_name} Level"
        )
        self._attr_unique_id = f"{entry.entry_id}_{vin}_heated_seat_{seat_id}_level"
        self._attr_options = ["Off", "Low", "Medium", "High"]

        self._device_info = create_device_info(coordinator, entry.entry_id)

    @property
    def device_info(self):
        """Return device info"""
        return self._device_info

    @property
    def icon(self):
        """Return the icon for the entity."""
        return self._icon

    @property
    def current_option(self):
        """Return the current heating level."""
        status = self.coordinator.data.get("status")
        if status:
            basic_status = getattr(status, "basicVehicleStatus", None)
            if basic_status:
                level = getattr(basic_status, f"{self._seat_id}SeatHeatLevel", 0)
                return {0: "Off", 1: "Low", 2: "Medium", 3: "High"}.get(level, "Off")
        return "Off"

    async def async_select_option(self, option: str):
        """Handle user selection to set the heating level."""
        level = {"Off": 0, "Low": 1, "Medium": 2, "High": 3}.get(option, 0)
        try:
            # Get the current level of the opposite seat
            current_status = self.coordinator.data.get("status", {})
            basic_status = getattr(current_status, "basicVehicleStatus", {})
            if self._seat_id == "frontLeft":
                right_side_level = getattr(basic_status, "frontRightSeatHeatLevel", 0)
                await self._client.control_heated_seats(
                    self._vin, level, right_side_level
                )
            elif self._seat_id == "frontRight":
                left_side_level = getattr(basic_status, "frontLeftSeatHeatLevel", 0)
                await self._client.control_heated_seats(
                    self._vin, left_side_level, level
                )
            LOGGER.info(
                "Set heating level '%s' (%d) for seat %s in VIN: %s",
                option,
                level,
                self._seat_id,
                self._vin,
            )
        except Exception as e:
            LOGGER.error(
                "Failed to set heating level '%s' for seat %s in VIN %s: %s",
                option,
                self._seat_id,
                self._vin,
                e,
            )
            raise

        # Schedule a refresh
        immediate_interval = self.coordinator.after_action_delay
        long_interval = self.coordinator.heated_seats_long_interval

        await self.coordinator.schedule_action_refresh(
            self._vin,
            immediate_interval,
            long_interval,
        )
