"""Data coordinator for My Team.

One refresh cycle tries the configured provider first, then the other one, and
only reports a failure when both are out. On top of that it keeps the last good
snapshot for a day, so a few hours of API trouble never blanks a dashboard.

Failover works even though the two APIs use different team ids: the coordinator
resolves (and caches) the matching team on the other provider by name, the first
time it actually needs it.

The poll interval is dynamic: the configured interval normally, 30 minutes in
the 12 hours before a match and 10 minutes from 30 minutes before kickoff until
3 hours after — so the lineup, half time and the final score show up quickly
without hammering either API all day.
"""

from __future__ import annotations

import inspect
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    ATTR_DEGRADED,
    CONF_API_KEY,
    CONF_BADGE,
    CONF_LEAGUE,
    CONF_PREFER_ESPN,
    CONF_PROVIDER,
    CONF_SCAN_INTERVAL,
    CONF_SPORT,
    CONF_TEAM_ID,
    CONF_TEAM_NAME,
    DEFAULT_API_KEY,
    DEFAULT_SCAN_INTERVAL,
    LIVE_INTERVAL,
    LIVE_WINDOW,
    MATCH_DAY_INTERVAL,
    MATCH_DAY_WINDOW,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    PROVIDER_ESPN,
    PROVIDER_THESPORTSDB,
)
from .providers import EspnProvider, ProviderError, TheSportsDBProvider

_LOGGER = logging.getLogger(__name__)

LAST_GOOD_TTL = timedelta(hours=24)
KICKOFF_SOON = 60 * 60          # seconds before kickoff that “live” polling starts

# `config_entry` became a supported (and eventually expected) DataUpdateCoordinator
# argument part-way through 2024 — detect it instead of breaking on either side.
_SUPPORTS_CONFIG_ENTRY = (
    "config_entry" in inspect.signature(DataUpdateCoordinator.__init__).parameters
)


def _clamp_minutes(value: Any) -> int:
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SCAN_INTERVAL
    return max(MIN_SCAN_INTERVAL, min(MAX_SCAN_INTERVAL, minutes))


class SportsTeamCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch next/last match for one team, with automatic provider failover."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.team_id = str(entry.data[CONF_TEAM_ID])
        self.team_name = entry.data.get(CONF_TEAM_NAME) or "Team"

        options = {**entry.data, **entry.options}
        self._provider_key = options.get(CONF_PROVIDER) or PROVIDER_THESPORTSDB
        self._api_key = str(options.get(CONF_API_KEY) or DEFAULT_API_KEY).strip()
        self._prefer_espn = bool(options.get(CONF_PREFER_ESPN))
        self._configured_interval = _clamp_minutes(
            options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )

        self.team: dict[str, Any] = {
            "provider": self._provider_key,
            "team_id": self.team_id,
            "team_name": self.team_name,
            "sport": options.get(CONF_SPORT),
            "league": options.get(CONF_LEAGUE),
            "league_name": options.get(CONF_LEAGUE),
            "badge": options.get(CONF_BADGE),
        }

        kwargs: dict[str, Any] = {
            "hass": hass,
            "logger": _LOGGER,
            "name": f"My Team - {self.team_name}",
            "update_interval": timedelta(minutes=self._configured_interval),
        }
        if _SUPPORTS_CONFIG_ENTRY:
            kwargs["config_entry"] = entry

        super().__init__(**kwargs)

        self._alt_teams: dict[str, dict[str, Any]] = {}
        self._last_good: dict[str, Any] | None = None
        self._last_good_at: datetime | None = None
        self._warned_degraded = False

    # ── providers ─────────────────────────────────────────────────────────────
    @property
    def provider_key(self) -> str:
        """The provider this entry was created with."""
        return self._provider_key

    def providers(self) -> list[Any]:
        """Providers in the order they should be tried."""
        session = async_get_clientsession(self.hass)
        tsdb = TheSportsDBProvider(session, self._api_key)
        espn = EspnProvider(session)

        if self._prefer_espn:
            return [espn, tsdb]
        if self._provider_key == PROVIDER_ESPN:
            return [espn, tsdb]
        return [tsdb, espn]

    async def _team_for(self, provider: Any) -> dict[str, Any]:
        """The team dict addressed for this provider (resolving the alt id)."""
        if provider.key == self.team.get("provider"):
            return self.team

        cached = self._alt_teams.get(provider.key)
        if cached:
            return cached

        matches = await provider.search(self.team_name)
        if not matches:
            raise ProviderError(
                f"{provider.label} has no team called {self.team_name!r}"
            )

        wanted = self.team_name.strip().lower()
        exact = [
            m
            for m in matches
            if str(m.get("team_name", "")).strip().lower() == wanted
        ]
        chosen = (exact or matches)[0]
        self._alt_teams[provider.key] = chosen
        _LOGGER.debug(
            "My Team: %s resolved to %s (%s) for failover",
            self.team_name,
            chosen.get("team_id"),
            provider.label,
        )
        return chosen

    # ── refresh ───────────────────────────────────────────────────────────────
    async def _async_update_data(self) -> dict[str, Any]:
        errors: list[str] = []
        snapshot: dict[str, Any] | None = None
        used: str | None = None

        for provider in self.providers():
            try:
                team = await self._team_for(provider)
                result = await provider.team_snapshot(team)
            except ProviderError as err:
                _LOGGER.debug(
                    "%s failed for %s: %s", provider.label, self.team_name, err
                )
                errors.append(f"{provider.label}: {err}")
                continue

            if not result.get("next") and not result.get("last"):
                errors.append(f"{provider.label}: no events returned")
                continue

            snapshot = result
            used = provider.key
            break

        if snapshot is None:
            return self._degraded_data(errors)

        payload = self._build_payload(snapshot, used or "unknown", errors)
        self._last_good = payload
        self._last_good_at = datetime.now(UTC)
        self._warned_degraded = False
        self._apply_interval(payload)
        return payload

    def _build_payload(
        self,
        snapshot: dict[str, Any],
        provider_key: str,
        errors: list[str],
    ) -> dict[str, Any]:
        team = snapshot.get("team") or self.team
        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "provider": provider_key,
            "primary_provider": self._provider_key,
            "team": team,
            "next": snapshot.get("next"),
            "last": snapshot.get("last"),
            "upcoming": snapshot.get("upcoming") or [],
            "updated": datetime.now(UTC).isoformat(),
            # degraded == "a source we wanted failed", not "the fallback answered
            # while the user prefers the other one"
            ATTR_DEGRADED: bool(errors),
            "errors": errors,
        }

    def _degraded_data(self, errors: list[str]) -> dict[str, Any]:
        """Both providers failed — serve the last good snapshot if it is fresh."""
        now = datetime.now(UTC)
        if self._last_good and self._last_good_at:
            if now - self._last_good_at <= LAST_GOOD_TTL:
                if not self._warned_degraded:
                    _LOGGER.warning(
                        "My Team: no provider answered for %s (%s) — keeping the "
                        "snapshot from %s",
                        self.team_name,
                        "; ".join(errors) or "unknown error",
                        self._last_good_at.strftime("%H:%M UTC"),
                    )
                    self._warned_degraded = True
                stale = dict(self._last_good)
                stale[ATTR_DEGRADED] = True
                stale["errors"] = errors
                return stale

        raise UpdateFailed(
            "No data for "
            f"{self.team_name}: "
            + ("; ".join(errors) if errors else "every provider returned nothing")
        )

    # ── smart polling ─────────────────────────────────────────────────────────
    def _apply_interval(self, payload: dict[str, Any]) -> None:
        """Speed up around kickoff, otherwise honour the configured interval."""
        minutes = self._configured_interval
        start: datetime | None = (payload.get("next") or {}).get("start")

        if start:
            delta = (start - datetime.now(UTC)).total_seconds()
            if -LIVE_WINDOW <= delta <= KICKOFF_SOON:
                minutes = min(minutes, LIVE_INTERVAL)
            elif KICKOFF_SOON < delta <= MATCH_DAY_WINDOW:
                minutes = min(minutes, MATCH_DAY_INTERVAL)

        interval = timedelta(minutes=minutes)
        if self.update_interval != interval:
            _LOGGER.debug(
                "My Team: next poll for %s in %s minutes", self.team_name, minutes
            )
            self.update_interval = interval
