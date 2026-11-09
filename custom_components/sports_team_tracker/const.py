"""Constants for the My Team integration."""

from __future__ import annotations

DOMAIN = "sports_team_tracker"
NAME = "My Team"
VERSION = "1.0.0"

# ── config keys ────────────────────────────────────────────────────────────────
CONF_TEAM_ID = "team_id"
CONF_TEAM_NAME = "team_name"
CONF_PROVIDER = "provider"
CONF_API_KEY = "api_key"
CONF_SPORT = "sport"
CONF_LEAGUE = "league"
CONF_BADGE = "badge"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_PREFER_ESPN = "prefer_espn"

# ── providers ──────────────────────────────────────────────────────────────────
PROVIDER_THESPORTSDB = "thesportsdb"
PROVIDER_ESPN = "espn"

PROVIDER_LABELS = {
    PROVIDER_THESPORTSDB: "TheSportsDB",
    PROVIDER_ESPN: "ESPN",
}

# TheSportsDB killed the old free key "3" (HTTP 403 "permanently disabled");
# "123" is the current free test key. A premium key can be set in the options.
DEFAULT_API_KEY = "123"

TSDB_BASE = "https://www.thesportsdb.com/api/v1/json"
TSDB_SEARCH = "searchteams.php"
TSDB_NEXT = "eventsnext.php"
TSDB_LAST = "eventslast.php"
TSDB_LOOKUP = "lookupteam.php"

ESPN_SITE = "https://site.api.espn.com/apis/site/v2/sports"
ESPN_SEARCH = "https://site.web.api.espn.com/apis/search/v2"

USER_AGENT = f"MyTeam-HA/{VERSION} (+https://github.com/Mkhimer69/My-Team)"

# ── polling ────────────────────────────────────────────────────────────────────
DEFAULT_SCAN_INTERVAL = 180          # minutes — the old hard-coded 3 hours
MIN_SCAN_INTERVAL = 15
MAX_SCAN_INTERVAL = 1440
MATCH_DAY_INTERVAL = 30              # minutes — kickoff is within 12 h
LIVE_INTERVAL = 10                   # minutes — kickoff is near / match is on
LIVE_WINDOW = 3 * 60 * 60            # seconds after kickoff still polled fast
MATCH_DAY_WINDOW = 12 * 60 * 60      # seconds before kickoff that “match day” starts

# ── misc ───────────────────────────────────────────────────────────────────────
ATTR_DEGRADED = "data_degraded"
DEFAULT_NAME = "My Team"
MANUFACTURER = "TheSportsDB · ESPN"
