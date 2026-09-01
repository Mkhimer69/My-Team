"""Sensors for Sports Team Tracker."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import SportsTeamCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for a team."""

    coordinator: SportsTeamCoordinator = (
        hass.data[DOMAIN][entry.entry_id]
    )

    async_add_entities(
        [
            NextMatchSensor(coordinator),
            MatchTimeSensor(coordinator),
        ]
    )


class SportsTeamSensor(
    CoordinatorEntity[SportsTeamCoordinator],
    SensorEntity,
):
    """Base sensor for a sports team."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SportsTeamCoordinator,
    ) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator)

        self._attr_device_info = {
            "identifiers": {
                (DOMAIN, coordinator.team_id)
            },
            "name": coordinator.team_name,
            "manufacturer": "TheSportsDB",
            "model": "Sports Team",
        }


class NextMatchSensor(SportsTeamSensor):
    """Sensor showing the team's next match."""

    _attr_name = "Next Match"
    _attr_icon = "mdi:soccer"

    def __init__(
        self,
        coordinator: SportsTeamCoordinator,
    ) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.team_id}_next_match"
        )

    @property
    def native_value(self) -> str:
        """Return the next match."""

        event = self.coordinator.data.get("event")

        if not event:
            return "No upcoming match"

        return event.get(
            "strEvent",
            "Unknown match",
        )

    def _local_match_time(self, event: dict[str, Any]) -> str | None:
        """Return the match time converted to Home Assistant's timezone."""

        timestamp = event.get("strTimestamp")

        if not timestamp:
            return None

        try:
            match_time = datetime.fromisoformat(timestamp).replace(tzinfo=UTC)
            return match_time.astimezone(
                dt_util.get_time_zone(self.hass.config.time_zone)
            ).strftime("%H:%M:%S")
        except (TypeError, ValueError):
            return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return match information."""

        event = self.coordinator.data.get("event")

        if not event:
            return {}

        return {
            "event_id": event.get("idEvent"),
            "league": event.get("strLeague"),
            "season": event.get("strSeason"),
            "home_team": event.get("strHomeTeam"),
            "away_team": event.get("strAwayTeam"),
            "home_team_id": event.get("idHomeTeam"),
            "away_team_id": event.get("idAwayTeam"),
            "date": event.get("dateEvent"),
            "api_time_utc": event.get("strTimestamp"),
            "local_time": self._local_match_time(event),
            "venue": event.get("strVenue"),
            "city": event.get("strCity"),
            "country": event.get("strCountry"),
            "status": event.get("strStatus"),
            "postponed": event.get("strPostponed"),
            "league_badge": event.get("strLeagueBadge"),
            "home_team_badge": event.get(
                "strHomeTeamBadge"
            ),
            "away_team_badge": event.get(
                "strAwayTeamBadge"
            ),
        }


class MatchTimeSensor(SportsTeamSensor):
    """Sensor showing the next match time."""

    _attr_name = "Match Time"
    _attr_icon = "mdi:calendar-clock"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: SportsTeamCoordinator,
    ) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.team_id}_match_time"
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the match time."""

        event = self.coordinator.data.get("event")

        if not event:
            return None

        timestamp = event.get("strTimestamp")

        if not timestamp:
            return None

        try:
            # TheSportsDB provides this timestamp as UTC.
            return datetime.fromisoformat(timestamp).replace(
                tzinfo=UTC
            )
        except ValueError:
            return None
