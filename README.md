# ⚽ My Team

A simple and lightweight **Home Assistant custom integration** for tracking your favorite football teams and their upcoming matches. **My Team** uses [The SportsDB](https://www.thesportsdb.com/) to retrieve upcoming fixture information and exposes it directly in Home Assistant, making it easy to build dashboards, automations, notifications, TV overlays, and match-day reminders.

---

## ✨ Features

- ⚽ Track multiple football teams
- 🔎 Search for teams during setup
- 📅 Automatically retrieve the next upcoming match
- 🕒 Dedicated match-time sensor
- 🌍 Match times converted to your Home Assistant timezone
- 🏆 League and competition information
- 🏟️ Stadium / venue information
- 📊 Match and team IDs
- 📅 Match date and season
- ⚽ Match status
- 🔄 Automatic fixture updates
- 🖼️ League badge
- 🛡️ Home team badge
- 🛡️ Away team badge
- 🏠 Native Home Assistant entities
- 🧩 HACS compatible

---

## 📦 Installation

### HACS
The recommended way to install **My Team** is through HACS.

#### Add My Team as a Custom Repository
1. Open **HACS** in Home Assistant.
2. Go to **Integrations**.
3. Open the **three-dot menu** in the top-right corner.
4. Select **Custom repositories**.
5. Add the following repository URL: `https://github.com/Mkhimer69/My-Team`
6. Select **Integration** as the category.
7. Click **Add**.
8. Search for **My Team**.
9. Install the integration.
10. Restart Home Assistant.

After restarting Home Assistant, go to: **Settings** → **Devices & Services** → **Add Integration** → **My Team**.

### 🛠️ Manual Installation
1. Download or clone this repository.
2. Copy the integration folder into your Home Assistant configuration directory. The integration must be located at: `/config/custom_components/sports_team_tracker/`

The folder structure should look like this:
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
        └── translations
            └── en.json
```
3. Restart Home Assistant after installation.

*Note: `sports_team_tracker` is the internal Home Assistant domain. The user-facing integration name is **My Team**.*

---

## ⚙️ Configuration

My Team uses Home Assistant's configuration flow, so no YAML configuration is required.

1. Go to **Settings** → **Devices & Services** → **Add Integration**.
2. Search for: **My Team**.
3. Enter the name of the football team you want to track.
4. My Team searches The SportsDB and presents matching teams for you to select.

Once you select a team, the integration creates the required Home Assistant entities automatically. You can add multiple teams independently. For example:
- ⚽ Al Ahly
- ⚽ Zamalek
- ⚽ Liverpool
- ⚽ Barcelona
- ⚽ Trabzonspor

---

## 📡 Sensors

Each configured team provides two sensors.

### ⚽ Next Match
The Next Match sensor contains information about the team's next upcoming fixture.

- **Example entity:** `sensor.al_ahly_next_match`
- **Example state:** `Al Ahly vs Smouha`

The sensor also exposes detailed match information through its attributes.

| Attribute | Description |
| :--- | :--- |
| `event_id` | Unique event ID |
| `league` | Competition/league name |
| `season` | Competition season |
| `home_team` | Home team |
| `away_team` | Away team |
| `home_team_id` | Home team ID |
| `away_team_id` | Away team ID |
| `date` | Match date |
| `api_time_utc` | Match time supplied by The SportsDB |
| `local_time` | Match time in the Home Assistant timezone |
| `venue` | Stadium/venue |
| `city` | Match city |
| `country` | Match country |
| `status` | Match status |
| `postponed` | Whether the match is postponed |
| `league_badge` | League badge URL |
| `home_team_badge` | Home team badge URL |
| `away_team_badge` | Away team badge URL |

**Attributes Example:**
```yaml
league: Egyptian Premier League
season: 2026-2027
home_team: Al Ahly
away_team: Smouha
date: 2026-09-03
local_time: 20:00:00
venue: Cairo International Stadium
status: NS
postponed: no
```

### 🕒 Match Time
The Match Time sensor provides the kickoff time of the next match as a Home Assistant timestamp.

- **Example entity:** `sensor.al_ahly_match_time`
- **Example state:** `2026-09-03T17:00:00+00:00`

The sensor uses Home Assistant's timestamp device class: `device_class: timestamp`. This makes it especially useful for automations and time-based dashboard cards. For example:

```yaml
triggers:
  - trigger: time
    at: sensor.al_ahly_match_time
```

You can use the timestamp sensor for:
- ⏰ Match reminders
- 📺 TV notifications
- 📱 Mobile notifications
- 📅 Dashboard cards
- ⏳ Countdown calculations
- ⚽ Match-day automations

---

## 🎨 Dashboard Example

The Next Match sensor exposes the league and team badge URLs, making it possible to create rich football dashboards directly from Home Assistant. 

The following Markdown card example displays multiple teams using their league and team badges:

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

This allows multiple teams to be displayed beautifully in a single card while automatically pulling the:
- 🏆 League badge
- 🛡️ Home team badge
- 🛡️ Away team badge
- 🕒 Local kickoff time
- 📅 Match date
- 🏆 Competition name

---

## 🤖 Automations

The Match Time sensor can be used directly within Home Assistant automations.

### Pre-Match / Kickoff Mobile Notification
```yaml
triggers:
  - trigger: time
    at: sensor.zamalek_match_time
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "⚽ Match Started"
      message: >
        {{ state_attr('sensor.zamalek_next_match', 'home_team') }} vs {{ state_attr('sensor.zamalek_next_match', 'away_team') }}
```

### 📺 TV Notifications & Overlays
My Team works particularly well with TV notification and live overlay integrations. The badge URLs exposed by the Next Match sensor can be used directly as notification artwork.

```yaml
action: notify.android_tv_fire_tv
data:
  title: "⚽ Match Center"
  message: >
    🏆 {{ state_attr('sensor.al_ahly_next_match', 'league') }}
    🏠 {{ state_attr('sensor.al_ahly_next_match', 'home_team') }} ⚔️ VS ✈️ {{ state_attr('sensor.al_ahly_next_match', 'away_team') }}
    🕒 {{ state_attr('sensor.al_ahly_next_match', 'local_time')[:5] }}
  data:
    image: >
      {{ state_attr('sensor.al_ahly_next_match', 'league_badge') }}
```

Because each team tracked generates its own independent sensors, you can create a single smart automation to track all your teams globally.

---

## 🔄 Data Updates

My Team periodically checks The SportsDB for the latest fixture information. 
- The integration currently refreshes its data every **3 hours**.
- When a match concludes, the integration automatically steps forward to the next available fixture. 

This ensures that your dashboards and automations continue running smoothly without needing any manual changes between match days.

---

## 🌐 Data Source

My Team uses **The SportsDB** for all underlying football data, fixtures, team identifiers, competitions, and badge imagery. Please refer to [The SportsDB](https://www.thesportsdb.com/) for information regarding their API access, data availability policies, and terms of use.

---

## 🐛 Troubleshooting

### My Team doesn't appear in HACS
- Make sure the repository has been added correctly as a **Custom repository**: `https://github.com/Mkhimer69/My-Team`
- Verify that you chose **Integration** as the repository category.
- Remember to restart Home Assistant after downloading via HACS.

### No team is found during search
Try searching using the team's official or most common name (e.g., *Al Ahly, Zamalek, Liverpool, Barcelona, Trabzonspor*). Available search results rely entirely on upstream data provided by The SportsDB.

### No upcoming match is shown
A team may not have an upcoming fixture available. Possible reasons include:
- No upcoming fixture has been published yet.
- The competition schedule is not yet available.
- The fixture has not yet been added to The SportsDB.
- The upstream data API is temporarily unavailable.

### Match information is incorrect or outdated
Football fixtures change frequently. Kickoff times, venues, competitions, and status states may be updated by leagues after a fixture is initially published. My Team automatically checks and periodically updates this data every 3 hours.

### Team badges are missing
Team and league artwork is provided by **TheSportsDB**. If a badge is missing, the corresponding artwork may not currently be available from the data provider.

---

## ❤️ Contributing

Contributions, suggestions, and bug reports are welcome. If you find a problem, please open an **Issue** on GitHub and include:
- Home Assistant version
- My Team version
- Team being tracked
- Affected match details
- Relevant Home Assistant logs

*Note: Please remove personal or sensitive information from logs before sharing them.*

---

## ⭐ Support the Project

If **My Team** is useful in your Home Assistant setup, consider giving the project a ⭐ on GitHub. It helps other Home Assistant users discover the integration and supports continued development.

***

<div align="center">
  <b>⚽ My Team</b><br>
  Your teams. Your matches. Your Home Assistant.
</div>

⚽ My Team

Your teams. Your matches. Your Home Assistant.
