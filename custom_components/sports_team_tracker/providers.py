"""Data providers for My Team.

Two independent sources, normalized into one shape so the coordinator, sensors and
diagnostics never care where a match came from:

* **TheSportsDB** — rich event metadata (badges, venue, season, status). Needs an
  API key: the old free ``"3"`` key is permanently disabled (HTTP 403), ``"123"``
  is the current free test key, and a premium key can be set in the options.
* **ESPN** — the public site API, no key, no quota worth worrying about. Used as
  the automatic fallback when TheSportsDB is down, rate-limited or out of luck,
  and as the first choice if the user prefers it.

Every function raises :class:`ProviderError` with a human-readable reason; the
coordinator turns that into a fallback attempt and, only if both fail, into an
``UpdateFailed``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import aiohttp

from .const import (
    DEFAULT_API_KEY,
    ESPN_SEARCH,
    ESPN_SITE,
    PROVIDER_ESPN,
    PROVIDER_THESPORTSDB,
    TSDB_BASE,
    TSDB_LAST,
    TSDB_NEXT,
    TSDB_SEARCH,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


class ProviderError(Exception):
    """A provider could not answer (network, quota, bad key, empty payload)."""


# ── small helpers ──────────────────────────────────────────────────────────────
def _as_int(value: Any) -> int | None:
    """Best-effort int, ``None`` for anything that isn't a number."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, dict):                      # ESPN wraps scores
        value = value.get("value", value.get("displayValue"))
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _parse_dt(value: Any) -> datetime | None:
    """Parse the several timestamp shapes both APIs use, always UTC-aware."""
    if not value:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none"}:
        return None
    text = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text[:19], fmt)
                break
            except ValueError:
                continue
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _event_key(event: dict[str, Any]) -> str:
    """Stable identity for de-duplication across refreshes."""
    return f"{event.get('provider')}:{event.get('id')}"


# ── normalization ──────────────────────────────────────────────────────────────
def parse_tsdb_event(event: dict[str, Any]) -> dict[str, Any]:
    """Normalize one TheSportsDB event."""
    start = _parse_dt(event.get("strTimestamp"))
    if start is None and event.get("dateEvent"):
        start = _parse_dt(
            f"{event['dateEvent']}T{event.get('strTime') or '00:00:00'}"
        )
    return {
        "provider": PROVIDER_THESPORTSDB,
        "id": str(event.get("idEvent") or ""),
        "name": event.get("strEvent") or "Unknown match",
        "start": start,
        "date": event.get("dateEvent"),
        "time": event.get("strTime"),
        "sport": event.get("strSport"),
        "league": event.get("strLeague"),
        "league_badge": event.get("strLeagueBadge"),
        "season": event.get("strSeason"),
        "round": event.get("intRound"),
        "home_team": event.get("strHomeTeam"),
        "away_team": event.get("strAwayTeam"),
        "home_id": event.get("idHomeTeam"),
        "away_id": event.get("idAwayTeam"),
        "home_score": _as_int(event.get("intHomeScore")),
        "away_score": _as_int(event.get("intAwayScore")),
        "status": event.get("strStatus"),
        "venue": event.get("strVenue"),
        "city": event.get("strCity"),
        "country": event.get("strCountry"),
        "badge": event.get("strThumb") or event.get("strEventThumb"),
        "home_badge": event.get("strHomeTeamBadge"),
        "away_badge": event.get("strAwayTeamBadge"),
        "postponed": event.get("strPostponed"),
    }


def parse_espn_event(
    event: dict[str, Any],
    *,
    sport: str | None = None,
    league: str | None = None,
) -> dict[str, Any]:
    """Normalize one ESPN event from a team schedule."""
    comp = (event.get("competitions") or [{}])[0]
    competitors = comp.get("competitors") or []

    def pick(side: str) -> dict[str, Any]:
        return next(
            (c for c in competitors if c.get("homeAway") == side),
            {},
        )

    home, away = pick("home"), pick("away")

    def team_of(side_event: dict[str, Any]) -> dict[str, Any]:
        return side_event.get("team") or {}

    def logo(side_event: dict[str, Any]) -> str | None:
        team = team_of(side_event)
        if team.get("logo"):
            return team["logo"]
        logos = team.get("logos") or []
        return logos[0].get("href") if logos else None

    status_type = (event.get("status") or {}).get("type") or {}
    venue = comp.get("venue") or {}
    address = venue.get("address") or {}
    season = (event.get("season") or {}).get("displayName")
    league_name = (
        league
        or (event.get("seasonType") or {}).get("name")
        or (event.get("season") or {}).get("displayName")
    )

    start = _parse_dt(event.get("date") or comp.get("date"))
    home_score = _as_int(home.get("score"))
    away_score = _as_int(away.get("score"))
    status = status_type.get("description") or status_type.get("detail")
    if not status and home_score is not None and away_score is not None:
        status = "Final"

    return {
        "provider": PROVIDER_ESPN,
        "id": str(event.get("id") or comp.get("id") or ""),
        "name": event.get("name") or "Unknown match",
        "start": start,
        "date": start.date().isoformat() if start else None,
        "time": start.strftime("%H:%M:%S") if start else None,
        "sport": sport,
        "league": league_name,
        "league_badge": None,
        "season": season,
        "round": (comp.get("notes") or [{}])[0].get("headline")
        if comp.get("notes")
        else None,
        "home_team": team_of(home).get("displayName"),
        "away_team": team_of(away).get("displayName"),
        "home_id": str(team_of(home).get("id") or "") or None,
        "away_id": str(team_of(away).get("id") or "") or None,
        "home_score": home_score,
        "away_score": away_score,
        "status": status,
        "venue": venue.get("fullName"),
        "city": address.get("city"),
        "country": address.get("country"),
        "badge": (comp.get("image") or {}).get("href") if comp.get("image") else None,
        "home_badge": logo(home),
        "away_badge": logo(away),
        "postponed": "yes" if status_type.get("name") == "STATUS_POSTPONED" else None,
    }


# ── HTTP ───────────────────────────────────────────────────────────────────────
async def _get_json(
    session: aiohttp.ClientSession,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    label: str,
) -> Any:
    """GET a JSON document, turning every failure into a ProviderError."""
    try:
        async with session.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        ) as response:
            text = await response.text()
            if response.status == 403 and "permanently disabled" in text.lower():
                raise ProviderError(
                    f"{label} rejected the API key (the old free key is dead — "
                    "use the key 123 or add a premium key in the options)"
                )
            if response.status == 429:
                raise ProviderError(f"{label} rate limit reached (HTTP 429)")
            if response.status >= 400:
                snippet = " ".join(text.split())[:160]
                raise ProviderError(f"{label} HTTP {response.status}: {snippet}")
            try:
                return json.loads(text)
            except json.JSONDecodeError as err:
                raise ProviderError(
                    f"{label} answered with something that is not JSON"
                ) from err
    except TimeoutError as err:
        raise ProviderError(f"{label} timed out") from err
    except aiohttp.ClientError as err:
        raise ProviderError(f"{label} unreachable: {err}") from err


# ── TheSportsDB ────────────────────────────────────────────────────────────────
class TheSportsDBProvider:
    """Primary provider — rich match metadata."""

    key = PROVIDER_THESPORTSDB
    label = "TheSportsDB"

    def __init__(self, session: aiohttp.ClientSession, api_key: str | None) -> None:
        self._session = session
        self._api_key = (api_key or DEFAULT_API_KEY).strip() or DEFAULT_API_KEY

    def _url(self, endpoint: str) -> str:
        return f"{TSDB_BASE}/{quote(self._api_key, safe='')}/{endpoint}"

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Search teams by name."""
        data = await _get_json(
            self._session,
            self._url(TSDB_SEARCH),
            params={"t": query},
            label=self.label,
        )
        teams = (data or {}).get("teams") or []
        results: list[dict[str, Any]] = []
        for team in teams:
            team_id = str(team.get("idTeam") or "")
            if not team_id:
                continue
            results.append(
                {
                    "provider": self.key,
                    "team_id": team_id,
                    "team_name": team.get("strTeam") or "Unknown team",
                    "sport": team.get("strSport"),
                    "league": team.get("strLeague"),
                    "badge": team.get("strTeamBadge") or team.get("strBadge"),
                    "subtitle": team.get("strLeague")
                    or team.get("strCountry")
                    or team.get("strSport"),
                }
            )
        return results

    async def team_snapshot(self, team: dict[str, Any]) -> dict[str, Any]:
        """Next + recent events for one team."""
        team_id = str(team["team_id"])
        next_data, last_data = await asyncio.gather(
            _get_json(
                self._session,
                self._url(TSDB_NEXT),
                params={"id": team_id},
                label=self.label,
            ),
            _get_json(
                self._session,
                self._url(TSDB_LAST),
                params={"id": team_id},
                label=self.label,
            ),
            return_exceptions=True,
        )

        errors: list[str] = []
        upcoming: list[dict[str, Any]] = []
        recent: list[dict[str, Any]] = []

        if isinstance(next_data, Exception):
            errors.append(str(next_data))
        else:
            upcoming = [
                parse_tsdb_event(ev)
                for ev in ((next_data or {}).get("events") or [])
                if ev
            ]

        if isinstance(last_data, Exception):
            errors.append(str(last_data))
        else:
            recent = [
                parse_tsdb_event(ev)
                for ev in ((last_data or {}).get("results") or [])
                if ev
            ]

        # both endpoints usually fail for the same reason (bad key, outage) —
        # report each distinct cause once instead of twice
        errors = list(dict.fromkeys(errors))
        if not upcoming and not recent and errors:
            raise ProviderError("; ".join(errors))
        if errors:
            _LOGGER.debug("TheSportsDB partial failure: %s", errors)

        upcoming.sort(key=lambda e: e["start"] or datetime.max.replace(tzinfo=UTC))
        recent.sort(key=lambda e: e["start"] or datetime.min.replace(tzinfo=UTC))

        return {
            "team": team,
            "next": next((e for e in upcoming if e["start"]), None),
            "last": recent[-1] if recent else None,
            "upcoming": [e for e in upcoming if e["start"]][:10],
        }

    async def check_key(self) -> bool:
        """Cheap probe used by the options flow."""
        await self.search("Arsenal")
        return True


# ── ESPN ───────────────────────────────────────────────────────────────────────
class EspnProvider:
    """Keyless fallback — the public ESPN site API."""

    key = PROVIDER_ESPN
    label = "ESPN"

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Search teams by name across every sport ESPN covers."""
        data = await _get_json(
            self._session,
            ESPN_SEARCH,
            params={"query": query, "limit": "15", "type": "team"},
            label=self.label,
        )
        results: list[dict[str, Any]] = []
        for block in (data or {}).get("results") or []:
            if block.get("type") != "team":
                continue
            for item in block.get("contents") or []:
                if item.get("type") != "team":
                    continue
                team_id = self._team_id(item)
                sport = item.get("sport")
                league = item.get("defaultLeagueSlug")
                if not team_id or not sport or not league:
                    continue
                results.append(
                    {
                        "provider": self.key,
                        "team_id": team_id,
                        "team_name": item.get("displayName") or "Unknown team",
                        "sport": sport,
                        "league": league,
                        "league_name": item.get("subtitle"),
                        "badge": (item.get("image") or {}).get("default"),
                        "subtitle": " · ".join(
                            part
                            for part in (item.get("subtitle"), item.get("sport", "").title())
                            if part
                        ),
                    }
                )
        return results

    @staticmethod
    def _team_id(item: dict[str, Any]) -> str | None:
        uid = str(item.get("uid") or "")
        if "~t:" in uid:
            return uid.rsplit("~t:", 1)[1]
        return str(item.get("id") or "") or None

    async def team_snapshot(self, team: dict[str, Any]) -> dict[str, Any]:
        """Next fixture plus the team's recent results.

        The schedule endpoint only carries *completed* games for some sports
        (soccer, for one), so the next fixture comes from the team endpoint's
        ``nextEvent`` and the schedule only supplies the results.
        """
        sport = team.get("sport")
        league = team.get("league")
        team_id = str(team["team_id"])
        if not sport or not league:
            raise ProviderError("ESPN needs the sport and league for this team")

        base = f"{ESPN_SITE}/{sport}/{league}/teams/{team_id}"
        league_label = team.get("league_name") or league

        team_data, schedule_data = await asyncio.gather(
            _get_json(self._session, base, label=self.label),
            _get_json(
                self._session,
                f"{base}/schedule",
                label=self.label,
            ),
            return_exceptions=True,
        )

        if isinstance(team_data, Exception) and isinstance(schedule_data, Exception):
            raise ProviderError(f"ESPN unreachable: {team_data}")

        now = datetime.now(UTC)
        upcoming: dict[str, dict[str, Any]] = {}
        finished: list[dict[str, Any]] = []

        # 1 · the next fixture (small payload, always current)
        if not isinstance(team_data, Exception):
            profile = (team_data or {}).get("team") or {}
            next_events = profile.get("nextEvent") or []
            if isinstance(next_events, dict):
                next_events = [next_events]
            for raw in next_events:
                parsed = parse_espn_event(raw, sport=sport, league=league_label)
                if parsed["start"]:
                    upcoming[parsed["id"] or parsed["name"]] = parsed

            record = profile.get("standingSummary")
            if record:
                team = {**team, "standing": record}
            summary = ((profile.get("record") or {}).get("items") or [{}])[0].get(
                "summary"
            )
            if summary:
                team = {**team, "record": summary}

        # 2 · the season schedule (results, plus any future games it carries)
        if not isinstance(schedule_data, Exception):
            for raw in (schedule_data or {}).get("events") or []:
                parsed = parse_espn_event(raw, sport=sport, league=league_label)
                start = parsed["start"]
                if not start:
                    continue
                if (start - now).total_seconds() >= -3 * 3600:
                    upcoming.setdefault(parsed["id"] or parsed["name"], parsed)
                else:
                    finished.append(parsed)

        if not upcoming and not finished:
            raise ProviderError(
                f"ESPN returned no fixtures for {team.get('team_name')}"
            )

        ordered_upcoming = sorted(upcoming.values(), key=lambda e: e["start"])
        finished.sort(key=lambda e: e["start"])

        return {
            "team": team,
            "next": ordered_upcoming[0] if ordered_upcoming else None,
            "last": finished[-1] if finished else None,
            "upcoming": ordered_upcoming[:10],
        }

    async def check_key(self) -> bool:
        await self.search("Arsenal")
        return True
