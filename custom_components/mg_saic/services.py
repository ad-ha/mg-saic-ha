# services.py

import asyncio
from homeassistant.core import HomeAssistant, ServiceCall
from .const import DOMAIN


async def async_setup_services(hass: HomeAssistant, client):
    """Set up the MG SAIC services."""

    async def async_handle_start_hvac(call: ServiceCall):
        await client.start_hvac()

    async def async_handle_stop_hvac(call: ServiceCall):
        await client.stop_hvac()

    async def async_handle_start_charging(call: ServiceCall):
        await client.control_charging("start")

    async def async_handle_stop_charging(call: ServiceCall):
        await client.control_charging("stop")

    hass.services.async_register(DOMAIN, "start_hvac", async_handle_start_hvac)
    hass.services.async_register(DOMAIN, "stop_hvac", async_handle_stop_hvac)
    hass.services.async_register(DOMAIN, "start_charging", async_handle_start_charging)
    hass.services.async_register(DOMAIN, "stop_charging", async_handle_stop_charging)
