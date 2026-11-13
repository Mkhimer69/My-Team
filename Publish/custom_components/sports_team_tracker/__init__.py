"""My Team — track any sports team in Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_API_KEY,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    DEFAULT_API_KEY,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PROVIDER_THESPORTSDB,
)
from .coordinator import SportsTeamCoordinator
from .frontend import async_setup_frontend

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up My Team from a config entry."""
    coordinator = SportsTeamCoordinator(hass, entry)

    # First refresh is allowed to fail softly: the coordinator keeps a previous
    # snapshot, and with no snapshot yet HA shows the entry as retrying instead
    # of failing the whole setup.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # the match card travels with the integration; serving it is best-effort and
    # never allowed to block setup
    await async_setup_frontend(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when the options change (key, interval, provider preference)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate a v1 entry (hard-coded free key, no options) to v2."""
    if entry.version > 2:
        # Downgrades are not supported — leave the entry alone.
        return False

    if entry.version == 1:
        data = {**entry.data}
        data.setdefault(CONF_PROVIDER, PROVIDER_THESPORTSDB)
        data.setdefault(CONF_API_KEY, DEFAULT_API_KEY)
        data.setdefault(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        hass.config_entries.async_update_entry(entry, data=data, version=2)

    return True
