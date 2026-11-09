"""Sensors for My Team."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_DEGRADED,
    DOMAIN,
    MANUFACTURER,
    PROVIDER_LABELS,
    VERSION,
)
from .coordinator import SportsTeamCoordinator

NO_MATCH = "No upcoming match"
NO_RESULT = "No recent result"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensors for one team."""
    coordinator: SportsTeamCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            NextMatchSensor(coordinator),
            MatchTimeSensor(coordinator),
            NextOpponentSensor(coordinator),
            LastResultSensor(coordinator),
        ]
    )


def _local(dt: datetime | None) -> datetime | None:
    return dt_util.as_local(dt) if dt else None


def _provider_label(key: str | None) -> str | None:
    return PROVIDER_LABELS.get(key or "", key)


def _team_is_home(team_name: str, event: dict[str, Any]) -> bool | None:
    """Whether our team is the home side (None when the names don't match)."""
    wanted = (team_name or "").strip().lower()
    home = str(event.get("home_team") or "").strip().lower()
    away = str(event.get("away_team") or "").strip().lower()
    if wanted and wanted == home:
        return True
    if wanted and wanted == away:
        return False
    return None


class SportsTeamSensor(CoordinatorEntity[SportsTeamCoordinator], SensorEntity):
    """Shared device + helpers for every My Team sensor."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SportsTeamCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        provider = _provider_label(coordinator.provider_key)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.team_id)},
            "name": coordinator.team_name,
            "manufacturer": MANUFACTURER,
            "model": f"Sports team · {provider}",
            "sw_version": VERSION,
        }

    # ── shared event helpers ──────────────────────────────────────────────────
    @property
    def _event(self) -> dict[str, Any] | None:
        return self.coordinator.data.get("next")

    @property
    def _team_name(self) -> str:
        return self.coordinator.team_name

    def _kickoff(self, event: dict[str, Any] | None) -> datetime | None:
        if not event:
            return None
        start = event.get("start")
        return start if isinstance(start, datetime) else None

    def _opponent(self, event: dict[str, Any] | None) -> str | None:
        if not event:
            return None
        is_home = _team_is_home(self._team_name, event)
        if is_home is True:
            return event.get("away_team")
        if is_home is False:
            return event.get("home_team")

        # Unknown side: the name that isn't ours.
        wanted = self._team_name.strip().lower()
        for key in ("home_team", "away_team"):
            candidate = str(event.get(key) or "")
            if candidate.strip().lower() != wanted and candidate:
                return candidate
        return None

    def _common_attrs(self, event: dict[str, Any] | None) -> dict[str, Any]:
        """Provider + health info every sensor carries."""
        data = self.coordinator.data
        return {
            "provider": _provider_label(data.get("provider")),
            ATTR_DEGRADED: bool(data.get(ATTR_DEGRADED)),
            "last_update": data.get("updated"),
        }

    def _event_attrs(self, event: dict[str, Any] | None) -> dict[str, Any]:
        if not event:
            return {}

        start = self._kickoff(event)
        local_start = _local(start)
        is_home = _team_is_home(self._team_name, event)
        opponent = self._opponent(event)

        return {
            "opponent": opponent,
            "home_away": "home" if is_home else "away" if is_home is False else None,
            "is_home": is_home,
            "league": event.get("league"),
            "season": event.get("season"),
            "round": event.get("round"),
            "status": event.get("status"),
            "date": event.get("date"),
            "kickoff_utc": start.isoformat() if start else None,
            "kickoff_local": local_start.isoformat() if local_start else None,
            "local_time": local_start.strftime("%H:%M") if local_start else None,
            "venue": event.get("venue"),
            "city": event.get("city"),
            "country": event.get("country"),
            "home_team": event.get("home_team"),
            "away_team": event.get("away_team"),
            "home_team_badge": event.get("home_badge"),
            "away_team_badge": event.get("away_badge"),
            "league_badge": event.get("league_badge"),
            "opponent_badge": (
                event.get("away_badge") if is_home else event.get("home_badge")
            ),
            "postponed": event.get("postponed"),
        }


class NextMatchSensor(SportsTeamSensor):
    """Human-readable name of the next match."""

    _attr_name = "Next Match"
    _attr_icon = "mdi:soccer"

    def __init__(self, coordinator: SportsTeamCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.team_id}_next_match"

    @property
    def native_value(self) -> str:
        event = self._event
        if not event:
            return NO_MATCH
        return event.get("name") or "Unknown match"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        event = self._event
        attrs = self._common_attrs(event)
        if not event:
            return {**attrs, "upcoming": self._upcoming()}
        return {**attrs, **self._event_attrs(event), "upcoming": self._upcoming()}

    def _upcoming(self) -> list[dict[str, Any]]:
        """The next few fixtures, for a dashboard list card."""
        events = self.coordinator.data.get("upcoming") or []
        return [
            {
                "name": e.get("name"),
                "date": e.get("date"),
                "kickoff_utc": (
                    e["start"].isoformat() if isinstance(e.get("start"), datetime) else None
                ),
                "league": e.get("league"),
            }
            for e in events[:5]
        ]


class MatchTimeSensor(SportsTeamSensor):
    """Kickoff as a native timestamp — the automation-friendly one."""

    _attr_name = "Match Time"
    _attr_icon = "mdi:calendar-clock"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: SportsTeamCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.team_id}_match_time"

    @property
    def native_value(self) -> datetime | None:
        start = self._kickoff(self._event)
        if start is None:
            return None
        return start.astimezone(UTC)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        event = self._event
        attrs = self._common_attrs(event)
        if not event:
            return attrs
        picked = self._event_attrs(event)
        return {
            **attrs,
            **{
                k: picked.get(k)
                for k in (
                    "opponent",
                    "home_away",
                    "league",
                    "venue",
                    "city",
                    "status",
                    "kickoff_local",
                    "local_time",
                    "opponent_badge",
                )
            },
        }


class NextOpponentSensor(SportsTeamSensor):
    """Just the opponent — handy for notifications and voice."""

    _attr_name = "Next Opponent"
    _attr_icon = "mdi:shield-outline"

    def __init__(self, coordinator: SportsTeamCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.team_id}_next_opponent"

    @property
    def native_value(self) -> str | None:
        event = self._event
        if not event:
            return None
        return self._opponent(event) or "Unknown opponent"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        event = self._event
        attrs = self._common_attrs(event)
        if not event:
            return attrs
        return {
            **attrs,
            **{
                k: v
                for k, v in self._event_attrs(event).items()
                if k
                in {
                    "home_away",
                    "is_home",
                    "league",
                    "kickoff_utc",
                    "kickoff_local",
                    "local_time",
                    "venue",
                    "opponent_badge",
                }
            },
        }


class LastResultSensor(SportsTeamSensor):
    """The most recent completed match and its score."""

    _attr_name = "Last Result"
    _attr_icon = "mdi:scoreboard-outline"

    def __init__(self, coordinator: SportsTeamCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.team_id}_last_result"

    @property
    def _last(self) -> dict[str, Any] | None:
        return self.coordinator.data.get("last")

    @staticmethod
    def _scoreline(event: dict[str, Any]) -> str:
        home = event.get("home_team") or "Home"
        away = event.get("away_team") or "Away"
        hs, as_ = event.get("home_score"), event.get("away_score")
        if hs is None or as_ is None:
            return f"{home} vs {away}"
        return f"{home} {hs}–{as_} {away}"

    def _outcome(self, event: dict[str, Any]) -> str | None:
        """W / D / L from our team's point of view."""
        hs, as_ = event.get("home_score"), event.get("away_score")
        if hs is None or as_ is None:
            return None
        is_home = _team_is_home(self._team_name, event)
        if is_home is None:
            return None
        ours, theirs = (hs, as_) if is_home else (as_, hs)
        if ours > theirs:
            return "W"
        if ours < theirs:
            return "L"
        return "D"

    @property
    def native_value(self) -> str:
        event = self._last
        if not event:
            return NO_RESULT
        return self._scoreline(event)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        event = self._last
        attrs = self._common_attrs(event)
        if not event:
            return attrs

        start = self._kickoff(event)
        local_start = _local(start)
        return {
            **attrs,
            **self._event_attrs(event),
            "outcome": self._outcome(event),
            "home_score": event.get("home_score"),
            "away_score": event.get("away_score"),
            "finished_local": local_start.isoformat() if local_start else None,
        }
