"""Config flow for My Team."""

from __future__ import annotations

import asyncio
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
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
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    PROVIDER_LABELS,
    PROVIDER_THESPORTSDB,
)
from .providers import EspnProvider, ProviderError, TheSportsDBProvider

SEARCH_FIELD = "team_search"


def _schema(default_search: str = "") -> vol.Schema:
    return vol.Schema(
        {vol.Required(SEARCH_FIELD, default=default_search): str}
    )


class SportsTeamConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle adding a team."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the flow."""
        self._results: dict[str, dict[str, Any]] = {}
        self._search_term = ""

    async def _search_all(self, query: str) -> tuple[list[dict[str, Any]], list[str]]:
        """Search TheSportsDB and ESPN at the same time."""
        session = async_get_clientsession(self.hass)
        tsdb = TheSportsDBProvider(session, DEFAULT_API_KEY)
        espn = EspnProvider(session)

        found = await asyncio.gather(
            tsdb.search(query), espn.search(query), return_exceptions=True
        )

        results: list[dict[str, Any]] = []
        errors: list[str] = []
        for provider, outcome in zip((tsdb, espn), found, strict=True):
            if isinstance(outcome, Exception):
                errors.append(f"{provider.label}: {outcome}")
                continue
            results.extend(outcome)

        # One row per (name, league): TheSportsDB wins the tie because it carries
        # the richer metadata (badges, venue, season).
        merged: dict[tuple[str, str], dict[str, Any]] = {}
        for item in results:
            key = (
                str(item.get("team_name", "")).strip().lower(),
                str(item.get("league_name") or item.get("league") or "").strip().lower(),
            )
            if key not in merged or item["provider"] == PROVIDER_THESPORTSDB:
                merged[key] = item

        ordered = sorted(
            merged.values(),
            key=lambda item: (
                item["team_name"].strip().lower() != query.strip().lower(),
                item["provider"] != PROVIDER_THESPORTSDB,
                item["team_name"].lower(),
            ),
        )
        return ordered, errors

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Ask for a team name, then show the matches."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = str(user_input.get(SEARCH_FIELD, "")).strip()
            if not query:
                errors["base"] = "team_not_found"
            else:
                results, provider_errors = await self._search_all(query)
                if not results:
                    errors["base"] = (
                        "cannot_connect" if provider_errors else "team_not_found"
                    )
                else:
                    self._results = {
                        f"{item['provider']}:{item['team_id']}": item
                        for item in results
                    }
                    self._search_term = query
                    return await self.async_step_select_team()

            return self.async_show_form(
                step_id="user",
                data_schema=_schema(query),
                errors=errors,
            )

        return self.async_show_form(step_id="user", data_schema=_schema())

    async def async_step_select_team(self, user_input: dict[str, Any] | None = None):
        """Pick one of the search results."""
        errors: dict[str, str] = {}

        if user_input is not None:
            key = user_input[CONF_TEAM_ID]
            team = self._results.get(key)
            if team is None:
                errors["base"] = "team_not_found"
            else:
                await self.async_set_unique_id(f"team_{team['team_id']}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=team["team_name"],
                    data={
                        CONF_TEAM_ID: team["team_id"],
                        CONF_TEAM_NAME: team["team_name"],
                        CONF_PROVIDER: team["provider"],
                        CONF_SPORT: team.get("sport"),
                        CONF_LEAGUE: team.get("league"),
                        CONF_BADGE: team.get("badge"),
                        CONF_API_KEY: DEFAULT_API_KEY,
                        CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
                    },
                )

        options = {
            key: f"{team['team_name']} — {team.get('subtitle') or team['provider']}"
            f" [{PROVIDER_LABELS.get(team['provider'], team['provider'])}]"
            for key, team in self._results.items()
        }

        if not options:
            return await self.async_step_user()

        return self.async_show_form(
            step_id="select_team",
            data_schema=vol.Schema({vol.Required(CONF_TEAM_ID): vol.In(options)}),
            description_placeholders={"count": str(len(options))},
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return SportsTeamOptionsFlow(config_entry)


class SportsTeamOptionsFlow(config_entries.OptionsFlow):
    """Options: API key, poll interval, provider preference.

    The entry is stored on the flow itself: HA 2024.6 has no ``config_entry``
    property on ``OptionsFlow``, and newer versions set it from the flow handler.
    Keeping our own reference works on both.
    """

    def __init__(self, config_entry: config_entries.ConfigEntry | None = None) -> None:
        """Initialize."""
        self._entry = config_entry

    def _current(self) -> dict[str, Any]:
        """Data + options of the entry being edited."""
        entry = self._entry or getattr(self, "config_entry", None)
        if entry is None:
            return {}
        return {**entry.data, **entry.options}

    async def _key_works(self, api_key: str) -> bool:
        """Probe TheSportsDB with the supplied key."""
        session = async_get_clientsession(self.hass)
        try:
            await TheSportsDBProvider(session, api_key).search("Arsenal")
        except ProviderError:
            return False
        return True

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = str(user_input.get(CONF_API_KEY, "")).strip()
            if api_key and not await self._key_works(api_key):
                errors["base"] = "invalid_api_key"

            if not errors:
                data = {
                    CONF_API_KEY: api_key or DEFAULT_API_KEY,
                    CONF_SCAN_INTERVAL: int(
                        user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                    ),
                    CONF_PREFER_ESPN: bool(user_input.get(CONF_PREFER_ESPN)),
                }
                return self.async_create_entry(title="", data=data)

        current = self._current()
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_API_KEY, default=current.get(CONF_API_KEY, DEFAULT_API_KEY)
                ): str,
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                ),
                vol.Optional(
                    CONF_PREFER_ESPN, default=bool(current.get(CONF_PREFER_ESPN))
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "used_key": "free test key (123)"
                if current.get(CONF_API_KEY, DEFAULT_API_KEY) == DEFAULT_API_KEY
                else "custom key",
                "primary": PROVIDER_LABELS.get(
                    current.get(CONF_PROVIDER, PROVIDER_THESPORTSDB), "TheSportsDB"
                ),
            },
        )
