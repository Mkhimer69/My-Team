"""Config flow for Sports Team Tracker."""

from __future__ import annotations

import aiohttp
import voluptuous as vol

from homeassistant import config_entries

from .const import (
    CONF_TEAM_ID,
    CONF_TEAM_NAME,
    DOMAIN,
    SEARCH_TEAMS_ENDPOINT,
)


class SportsTeamConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle configuration of Sports Team Tracker."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""

        self._teams: list[dict] = []

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ):
        """Ask the user to search for a team."""

        if user_input is not None:
            team_search = user_input["team_search"].strip()

            if not team_search:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {
                            vol.Required(
                                "team_search"
                            ): str,
                        }
                    ),
                    errors={
                        "base": "team_not_found"
                    },
                )

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        SEARCH_TEAMS_ENDPOINT,
                        params={"t": team_search},
                        timeout=30,
                    ) as response:
                        response.raise_for_status()
                        data = await response.json()

            except (aiohttp.ClientError, TimeoutError):
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {
                            vol.Required(
                                "team_search"
                            ): str,
                        }
                    ),
                    errors={
                        "base": "cannot_connect"
                    },
                )

            self._teams = data.get("teams") or []

            if not self._teams:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {
                            vol.Required(
                                "team_search"
                            ): str,
                        }
                    ),
                    errors={
                        "base": "team_not_found"
                    },
                )

            return await self.async_step_select_team()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "team_search"
                    ): str,
                }
            ),
        )

    async def async_step_select_team(
        self,
        user_input: dict | None = None,
    ):
        """Allow the user to select a team."""

        if user_input is not None:
            team_id = user_input[CONF_TEAM_ID]

            team = next(
                team
                for team in self._teams
                if str(team["idTeam"]) == team_id
            )

            await self.async_set_unique_id(
                f"team_{team_id}"
            )

            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=team["strTeam"],
                data={
                    CONF_TEAM_ID: team["idTeam"],
                    CONF_TEAM_NAME: team["strTeam"],
                },
            )

        team_options = {
            str(team["idTeam"]): team["strTeam"]
            for team in self._teams
        }

        return self.async_show_form(
            step_id="select_team",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TEAM_ID
                    ): vol.In(team_options),
                }
            ),
        )
