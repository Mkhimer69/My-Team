"""Data coordinator for Sports Team Tracker."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from aiohttp import ClientError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import NEXT_EVENTS_ENDPOINT

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(hours=3)


class SportsTeamCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch upcoming match information for a team."""

    def __init__(
        self,
        hass,
        team_id: str,
        team_name: str,
    ) -> None:
        """Initialize the coordinator."""

        self.team_id = str(team_id)
        self.team_name = team_name

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"Sports Team Tracker - {team_name}",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the team's next match."""

        session = async_get_clientsession(self.hass)

        try:
            async with session.get(
                NEXT_EVENTS_ENDPOINT,
                params={"id": self.team_id},
                timeout=30,
            ) as response:
                response.raise_for_status()
                data = await response.json()

        except (ClientError, TimeoutError) as err:
            raise UpdateFailed(
                f"Unable to retrieve data for {self.team_name}"
            ) from err

        events = data.get("events") or []

        return {
            "team_id": self.team_id,
            "team_name": self.team_name,
            "event": events[0] if events else None,
        }
