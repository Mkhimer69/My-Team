"""Diagnostics for My Team — everything needed to debug, with the key redacted."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_API_KEY, DOMAIN, VERSION
from .coordinator import SportsTeamCoordinator

REDACTED = "**REDACTED**"


def _clean(value: Any) -> Any:
    """Make coordinator data JSON-safe for the diagnostics download."""
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _redact(data: dict[str, Any]) -> dict[str, Any]:
    clean = dict(data)
    if CONF_API_KEY in clean:
        clean[CONF_API_KEY] = REDACTED
    return clean


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: SportsTeamCoordinator = hass.data[DOMAIN][entry.entry_id]

    return {
        "integration": {"domain": DOMAIN, "version": VERSION},
        "entry": {
            "version": entry.version,
            "data": _redact(entry.data),
            "options": _redact(entry.options),
        },
        "coordinator": {
            "provider": coordinator.provider_key,
            "update_interval_minutes": (
                coordinator.update_interval.total_seconds() / 60
                if coordinator.update_interval
                else None
            ),
            "last_update_success": coordinator.last_update_success,
            "last_exception": str(coordinator.last_exception)
            if coordinator.last_exception
            else None,
            "data": _clean(coordinator.data or {}),
        },
    }
