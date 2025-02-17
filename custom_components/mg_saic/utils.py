# File: utils.py

from .const import DOMAIN


def create_device_info(coordinator, entry_id):
    """Generate device info the integration."""
    try:
        vin_info = coordinator.vin_info
        return {
            "identifiers": {(DOMAIN, vin_info.vin)},
            "name": f"{vin_info.brandName} {vin_info.modelName}",
            "manufacturer": vin_info.brandName,
            "model": vin_info.modelName,
            "serial_number": vin_info.vin,
        }
    except (IndexError, KeyError, AttributeError) as e:
        raise ValueError(f"Failed to create device info: {e}")
