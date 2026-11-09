"""Binary sensor for My Team — is it match day?"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ATTR_DEGRADED, DOMAIN, MANUFACTURER, PROVIDER_LABELS, VERSION
from .coordinator import SportsTeamCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the match-day binary sensor."""
    coordinator: SportsTeamCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MatchDaySensor(coordinator)])


class MatchDaySensor(CoordinatorEntity[SportsTeamCoordinator], BinarySensorEntity):
    """On from midnight to midnight on the day of the next match."""

    _attr_has_entity_name = True
    _attr_name = "Match Day"
    _attr_icon = "mdi:stadium"

    def __init__(self, coordinator: SportsTeamCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.team_id}_match_day"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.team_id)},
            "name": coordinator.team_name,
            "manufacturer": MANUFACTURER,
            "model": "Sports team",
            "sw_version": VERSION,
        }

    @property
    def _event(self) -> dict[str, Any] | None:
        return self.coordinator.data.get("next")

    def _kickoff(self) -> datetime | None:
        event = self._event or {}
        start = event.get("start")
        return start if isinstance(start, datetime) else None

    @property
    def is_on(self) -> bool:
        """True when the next match kicks off today (HA local time)."""
        start = self._kickoff()
        if start is None:
            return False
        return dt_util.as_local(start).date() == dt_util.now().date()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        event = self._event or {}
        start = self._kickoff()
        local = dt_util.as_local(start) if start else None

        return {
            "opponent": event.get("home_team")
            if event.get("home_team") != self.coordinator.team_name
            else event.get("away_team"),
            "league": event.get("league"),
            "venue": event.get("venue"),
            "status": event.get("status"),
            "kickoff_local": local.isoformat() if local else None,
            "provider": PROVIDER_LABELS.get(data.get("provider"), data.get("provider")),
            ATTR_DEGRADED: bool(data.get(ATTR_DEGRADED)),
        }
