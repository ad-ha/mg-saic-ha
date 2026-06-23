# File: __init__.py

import asyncio
from contextlib import suppress

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import SAICMGAPIClient
from .coordinator import SAICMGDataUpdateCoordinator
from .message_poller import SAICMGAccountPoller
from .const import DOMAIN, LOGGER, PLATFORMS
from .services import async_setup_services, async_unload_services

# ── Domain-level hass.data structure ─────────────────────────────────────────
#
# hass.data[DOMAIN] = {
#   # Per-entry resources (keyed by entry.entry_id)
#   "<entry_id>":             SAICMGAPIClient
#   "<entry_id>_coordinator": SAICMGDataUpdateCoordinator
#
#   # Global VIN → resource maps (for service resolution)
#   "clients_by_vin":         { vin: SAICMGAPIClient }
#   "coordinators_by_vin":    { vin: SAICMGDataUpdateCoordinator }
#
#   # Account-level singletons keyed by (username, region)
#   "account_pollers":        { account_key: SAICMGAccountPoller }
#   "account_locks":          { account_key: asyncio.Lock }
#   "account_login_locks":    { account_key: asyncio.Lock }
#
#   "services_registered":    bool
# }
#
# The account_lock serialises all API calls (data fetch + message poll) that
# share the same SAIC session, preventing token invalidation races when two
# VINs on the same account refresh concurrently.
#
# The account_login_lock serialises the initial login for each account so that
# if two config entries for the same account load simultaneously (HA startup),
# they share one login attempt rather than racing each other and invalidating
# one another's session tokens — this is the root cause of issue #147.


def _account_key(entry: ConfigEntry) -> tuple[str, str]:
    """Return a hashable identifier for the SAIC account behind *entry*."""
    return (entry.data["username"], entry.data.get("region", ""))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MG SAIC from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    domain = hass.data[DOMAIN]
    domain.setdefault("clients_by_vin", {})
    domain.setdefault("coordinators_by_vin", {})
    domain.setdefault("account_pollers", {})
    domain.setdefault("account_locks", {})
    domain.setdefault("account_login_locks", {})
    domain.setdefault("services_registered", False)

    username = entry.data["username"]
    password = entry.data["password"]
    vin = entry.data.get("vin")
    region = entry.data.get("region")
    username_is_email = entry.data.get("country_code") is None
    acct_key = _account_key(entry)

    # ── Ensure per-account singletons exist ──────────────────────────────────
    # account_lock: held during every API call on this account.
    # account_login_lock: held only during the login sequence so that two
    # entries for the same account starting simultaneously share one login.
    if acct_key not in domain["account_locks"]:
        domain["account_locks"][acct_key] = asyncio.Lock()
    if acct_key not in domain["account_login_locks"]:
        domain["account_login_locks"][acct_key] = asyncio.Lock()

    api_lock = domain["account_locks"][acct_key]
    login_lock = domain["account_login_locks"][acct_key]

    # ── Login (serialised per account) ───────────────────────────────────────
    # Holding login_lock means only one config entry per account attempts login
    # at a time.  If a second entry for the same account arrives while the
    # first is logging in, it waits and then shares the same live session via
    # its own SAICMGAPIClient (each entry still has its own client instance,
    # but they authenticate sequentially so neither invalidates the other).
    async with login_lock:
        client = SAICMGAPIClient(
            username,
            password,
            vin,
            username_is_email,
            region,
            entry.data.get("country_code"),
        )
        try:
            await client.login()
        except Exception as exc:
            LOGGER.error(
                "Failed to log in to MG SAIC for VIN %s (account %s): %s",
                vin,
                username,
                exc,
            )
            return False

    if not vin:
        LOGGER.error("No VIN specified in Config Entry")
        return False

    try:
        vehicles = await client.get_vehicle_info()
        if not any(v.vin == vin for v in vehicles):
            LOGGER.error("VIN %s not found in account vehicles", vin)
            return False
    except Exception as exc:
        LOGGER.error("Failed to verify VIN %s: %s", vin, exc)
        return False

    # Store per-entry client
    domain[entry.entry_id] = client

    # ── Build and wire up the coordinator ────────────────────────────────────
    coordinator = SAICMGDataUpdateCoordinator(hass, client, entry)
    # Inject the shared API lock before setup so _async_update_data can use it
    coordinator.set_api_lock(api_lock)

    try:
        await coordinator.async_setup()
    except Exception as exc:
        LOGGER.error("Coordinator setup failed for VIN %s: %s", vin, exc)
        return False

    domain[f"{entry.entry_id}_coordinator"] = coordinator
    domain["clients_by_vin"][vin] = client
    domain["coordinators_by_vin"][vin] = coordinator

    # ── Account-level message poller ─────────────────────────────────────────
    # One SAICMGAccountPoller per (username, region) regardless of VIN count.
    # It registers set_alarm_switches for each VIN and polls get_alarm_messages
    # once per minute for the whole account, routing events to the correct
    # coordinator by VIN.
    if acct_key not in domain["account_pollers"]:
        LOGGER.debug(
            "Creating new AccountPoller for account %s (first VIN: %s)",
            acct_key,
            vin,
        )
        poller = SAICMGAccountPoller(hass, client, acct_key, api_lock)
        domain["account_pollers"][acct_key] = poller
    else:
        LOGGER.debug(
            "Reusing existing AccountPoller for account %s (adding VIN: %s)",
            acct_key,
            vin,
        )
        poller = domain["account_pollers"][acct_key]

    poller.register_coordinator(vin, coordinator)

    # Start (or no-op if already running) the poller background task.
    # We pass this entry as the task owner — HA will cancel it on unload if
    # we somehow miss async_stop in async_unload_entry.
    poller.start(entry)

    # ── Register alarm switches for this VIN ─────────────────────────────────
    # Tells the SAIC server to queue event messages for us.  Done here (not in
    # coordinator.async_setup) so it uses the shared api_lock and doesn't race
    # concurrent logins on multi-VIN accounts.
    try:
        async with api_lock:
            await asyncio.wait_for(
                client.set_alarm_switches(vin=vin),
                timeout=30,
            )
    except asyncio.TimeoutError:
        LOGGER.warning(
            "set_alarm_switches timed out for VIN %s — "
            "message-driven updates may not function until next restart",
            vin,
        )
    except Exception as exc:
        LOGGER.warning(
            "set_alarm_switches failed for VIN %s: %s — "
            "message-driven updates may not function until next restart",
            vin,
            exc,
        )

    # ── Finalise ─────────────────────────────────────────────────────────────
    entry.async_on_unload(entry.add_update_listener(update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not domain["services_registered"]:
        await async_setup_services(hass)
        domain["services_registered"] = True

    LOGGER.info(
        "MG SAIC integration setup completed for VIN %s (account %s, %d VIN(s) on poller)",
        vin,
        acct_key,
        len(poller._coordinators),
    )
    return True


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    coordinator = hass.data[DOMAIN][f"{entry.entry_id}_coordinator"]
    await coordinator.async_update_options(entry.options)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    domain = hass.data[DOMAIN]
    vin = entry.data.get("vin")
    acct_key = _account_key(entry)

    # ── Coordinator shutdown ──────────────────────────────────────────────────
    coordinator = domain.pop(f"{entry.entry_id}_coordinator", None)
    client = domain.pop(entry.entry_id, None)

    if vin:
        domain.get("clients_by_vin", {}).pop(vin, None)
        domain.get("coordinators_by_vin", {}).pop(vin, None)

    if coordinator is not None:
        await coordinator.async_shutdown()

    # ── Poller VIN deregistration ─────────────────────────────────────────────
    poller = domain.get("account_pollers", {}).get(acct_key)
    if poller is not None and vin:
        poller.unregister_coordinator(vin)
        LOGGER.debug(
            "VIN %s unregistered from AccountPoller %s (%d remaining)",
            vin,
            acct_key,
            len(poller._coordinators),
        )
        # Stop and remove the poller only when the last VIN for this account
        # has been unloaded.  If other VINs remain, leave it running.
        if not poller.has_coordinators:
            LOGGER.info(
                "Last VIN unloaded for account %s — stopping AccountPoller",
                acct_key,
            )
            await poller.async_stop()
            domain["account_pollers"].pop(acct_key, None)
            domain["account_locks"].pop(acct_key, None)
            domain["account_login_locks"].pop(acct_key, None)

    if client is not None:
        with suppress(Exception):
            await client.close()

    # ── Global cleanup when no entries remain ─────────────────────────────────
    if not domain.get("clients_by_vin"):
        await async_unload_services(hass)
        for key in (
            "clients_by_vin",
            "coordinators_by_vin",
            "account_pollers",
            "account_locks",
            "account_login_locks",
            "services_registered",
        ):
            domain.pop(key, None)

    if not domain:
        hass.data.pop(DOMAIN, None)

    return True
