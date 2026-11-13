# Changelog

All notable changes to **My Team** are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/) and
[Semantic Versioning](https://semver.org/).

## [1.1.0] — 2026-11-13

### Added
- **A match card that ships with the integration** — `custom:sports-team-card`.
  League badge, `Home vs Away`, kickoff and a live countdown, flipping to
  **LIVE NOW** at kickoff. No Mushroom, no card-mod, nothing to copy and paste.
- The card is served from the integration at
  `/sports_team_tracker/sports-team-card.js` and registered as a dashboard
  resource automatically on setup; YAML-mode dashboards get the one-line manual
  step in the README.
- Optional `accent` (left border colour) and `show_venue` card options.

### Fixed
- `manifest.json` reported `0.3.0` while `const.py` said `1.0.0`; both now carry
  the same version, so Home Assistant and HACS show one number.

## [0.3.0] — 2026-11-09

### Fixed
- **The integration stopped working because TheSportsDB permanently disabled the
  free API key `3`** — every request returned `HTTP 403: The old '3' Free Sports
  API key is permanently disabled`. The default key is now `123` (the current free
  test key) and can be overridden with a premium key in the options.
- Real errors are reported instead of a generic "Unable to retrieve data": the
  HTTP status and the API's own message are surfaced in the log and in
  diagnostics.
- `next(...)` over the search results could raise `StopIteration` and crash the
  config flow; an unknown selection now shows a proper error.
- The config flow opened its own `aiohttp.ClientSession` and never closed it; it
  now uses Home Assistant's shared session.
- Config flow search no longer fails when one provider is down — results come
  from whichever source answers.

### Added
- **Automatic provider failover.** TheSportsDB is tried first, then ESPN (the
  public site API, no key, no quota worth worrying about). If both fail, the last
  good snapshot is served for up to 24 hours with `data_degraded: true`.
- **Failover across team ids**: the matching team on the other provider is
  resolved by name and cached, so either source can answer for any team.
- `sensor.<team>_next_opponent` and `sensor.<team>_last_result` (with W/D/L).
- `binary_sensor.<team>_match_day` for match-day automations.
- The next five fixtures as an `upcoming` attribute.
- **Options flow**: API key, poll interval (15 min – 24 h) and "try ESPN first".
- **Smart polling**: 30 minutes in the 12 hours before kickoff, 10 minutes from
  an hour before the match until 3 hours after it, your interval otherwise.
- `diagnostics.py` with the API key redacted.
- Automatic **config-entry migration** (v1 → v2), so existing installs need no
  action.
- Live badges, venue, city, season, round, status and `kickoff_local` on the
  sensors.

### Changed
- `manifest.json`: version 1.0.0, `integration_type`, `loggers`, codeowner.
- `hacs.json`: minimum Home Assistant 2024.6.
- README rewritten around the two sources, the new entities and troubleshooting.

## [0.2.0]
- Next-match and kickoff-time sensors on TheSportsDB, config-flow setup.
