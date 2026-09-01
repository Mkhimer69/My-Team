"""Constants for the Sports Team Tracker integration."""

DOMAIN = "sports_team_tracker"

CONF_TEAM_ID = "team_id"
CONF_TEAM_NAME = "team_name"

API_BASE = "https://www.thesportsdb.com/api/v1/json/3"

SEARCH_TEAMS_ENDPOINT = f"{API_BASE}/searchteams.php"
NEXT_EVENTS_ENDPOINT = f"{API_BASE}/eventsnext.php"

DEFAULT_SCAN_INTERVAL = 3
