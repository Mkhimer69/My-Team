<div align="center">

# ⚽ My Team

**A lightweight Home Assistant integration for tracking your favorite
football teams and their upcoming matches.**

Powered by [TheSportsDB](https://www.thesportsdb.com/) · Native HA entities · Config-flow setup

![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?logo=home-assistant&logoColor=white)
![Release](https://img.shields.io/github/v/release/Mkhimer69/My-Team)
![Stars](https://img.shields.io/github/stars/Mkhimer69/My-Team?style=flat)
![License](https://img.shields.io/badge/license-MIT-green)

</div>

---

Fixtures, kickoff times, venues and badges for **any team** — Al Ahly, Zamalek,
Liverpool, Barcelona, Trabzonspor… — straight into your dashboards, TV overlays
and match-day automations. No YAML required.

## ✨ Features
- ⚽ Track **multiple teams**, each with its own entities
- 🔎 Team search built into the config flow
- 📅 Next upcoming match, auto-advancing when a match ends
- 🕒 Kickoff time as a native **timestamp sensor** (automation-ready)
- 🌍 All times converted to your Home Assistant timezone
- 🏟️ Venue, city, league, season & match status
- 🖼️ League + team **badge URLs** for rich dashboards & notification artwork
- 🔄 Automatic refresh every 3 hours
- 🧩 HACS compatible

## 📦 Installation

### HACS (recommended)
1. HACS → **Integrations** → ⋮ menu → **Custom repositories**
2. Add `https://github.com/Mkhimer69/My-Team` — category: **Integration**
3. Install **My Team** → restart Home Assistant
4. **Settings → Devices & Services → Add Integration → My Team**

[![Open your Home Assistant instance and set up My Team](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sports_team_tracker)

### Manual
Copy the integration folder into your configuration directory, then restart:

```text
/config
└── custom_components
    └── sports_team_tracker
        ├── __init__.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── manifest.json
        ├── sensor.py
        ├── strings.json
        └── translations / en.json
```

> `sports_team_tracker` is the internal HA domain — the user-facing name is **My Team**.

## ⚙️ Configuration
No YAML — full config flow. Enter a team name, pick it from the search results,
done. Repeat for as many teams as you like.

## 📡 Sensors

Each tracked team creates **two sensors**:

### ⚽ Next Match — `sensor.al_ahly_next_match`
State: `Al Ahly vs Smouha`

| Attribute | Description |
|---|---|
| `home_team` / `away_team` | Team names |
| `league` / `season` | Competition info |
| `date` / `api_time_utc` / `local_time` | Kickoff details |
| `venue` / `city` / `country` | Where |
| `status` / `postponed` | Match state |
| `league_badge` / `home_team_badge` / `away_team_badge` | Artwork URLs |
| `event_id` / `home_team_id` / `away_team_id` | IDs |

### 🕒 Match Time — `sensor.al_ahly_match_time`
State: `2026-09-03T17:00:00+00:00` — device class **timestamp**, perfect for
time-based triggers (`trigger: time / at: sensor.al_ahly_match_time`), countdowns
and match-day automations.

## 🎨 Dashboard Example

A single Markdown card renders your whole match day with league & team badges:

```yaml
type: markdown
content: >
  {% set sensors = [
  'sensor.al_ahly_next_match',
  'sensor.barcelona_next_match',
  'sensor.liverpool_next_match',
  'sensor.zamalek_next_match_2'
  ] %}
  {% for sensor in sensors %}
  {% if states(sensor) != 'unknown' and state_attr(sensor, 'home_team') != None %}
  <div align="center">
  <img src="{{ state_attr(sensor, 'league_badge') }}" height="52">
  <br><sub>{{ state_attr(sensor, 'league') }}</sub>
  </div>
  <table width="100%">
  <tr>
  <td width="40%" align="center">
  <img src="{{ state_attr(sensor, 'home_team_badge') }}" height="60">
  <br><b>{{ state_attr(sensor, 'home_team') }}</b>
  </td>
  <td width="20%" align="center">
  <h2>{{ state_attr(sensor, 'local_time')[:5] }}</h2>
  <sub>{{ as_timestamp(strptime(state_attr(sensor, 'date'), '%Y-%m-%d', now())) | timestamp_custom('%d %b') }}</sub>
  </td>
  <td width="40%" align="center">
  <img src="{{ state_attr(sensor, 'away_team_badge') }}" height="60">
  <br><b>{{ state_attr(sensor, 'away_team') }}</b>
  </td>
  </tr>
  </table>
  {% if not loop.last %}<hr>{% endif %}
  {% endif %}
  {% endfor %}
```

## 🤖 Automations

**Kickoff notification**
```yaml
triggers:
- trigger: time
  at: sensor.zamalek_match_time
actions:
- action: notify.mobile_app_your_phone
  data:
    title: "⚽ Match Started"
    message: >
      {{ state_attr('sensor.zamalek_next_match', 'home_team') }} vs
      {{ state_attr('sensor.zamalek_next_match', 'away_team') }}
```

**TV overlay with artwork** (works great with Android TV / Fire TV notifications)
```yaml
action: notify.android_tv_fire_tv
data:
  title: "⚽ Match Center"
  message: >
    🏆 {{ state_attr('sensor.al_ahly_next_match', 'league') }}
    🏠 {{ state_attr('sensor.al_ahly_next_match', 'home_team') }} ⚔️
    ✈️ {{ state_attr('sensor.al_ahly_next_match', 'away_team') }}
    🕒 {{ state_attr('sensor.al_ahly_next_match', 'local_time')[:5] }}
  data:
    image: "{{ state_attr('sensor.al_ahly_next_match', 'league_badge') }}"
```

## 🔄 Data Updates
Fixtures refresh every **3 hours**; when a match ends, the integration
automatically advances to the next fixture. All football data is provided by
[TheSportsDB](https://www.thesportsdb.com/) — check their site for API terms.

## 🐛 Troubleshooting

| Problem | Fix |
|---|---|
| Not in HACS | Verify the custom repo URL + **Integration** category, then restart HA |
| Team not found in search | Try the official/common name; results depend on TheSportsDB |
| No upcoming match | Fixture may not be published yet, or upstream API is down |
| Wrong/old match info | Data refreshes every 3 h; leagues do change schedules |
| Missing badges | Artwork comes from TheSportsDB — some teams lack artwork upstream |

## ❤️ Contributing
Issues and PRs are welcome. When reporting a bug include: HA version, My Team
version, tracked team, and relevant logs (**remove sensitive data first**).

## ⭐ Support
If My Team is useful in your setup, give it a ⭐ — it helps others find it.

## 📄 License
MIT — © 2026 [Fathy Mkhimer](https://github.com/Mkhimer69)

---

<div align="center">
<b>⚽ My Team</b><br><i>Your teams. Your matches. Your Home Assistant.</i>
</div>
