⚽ My Team

A simple and lightweight Home Assistant custom integration for tracking your favorite football teams and their upcoming matches.

My Team uses TheSportsDB to retrieve upcoming fixture information and exposes it directly in Home Assistant, making it easy to build dashboards, automations, notifications, TV overlays, and match-day reminders.

✨ Features
⚽ Track multiple football teams
🔎 Search for teams during setup
📅 Automatically retrieve the next upcoming match
🕒 Dedicated match-time sensor
🌍 Match times converted to your Home Assistant timezone
🏆 League and competition information
🏟️ Stadium / venue information
📊 Match and team IDs
📅 Match date and season
⚽ Match status
🔄 Automatic fixture updates
🖼️ League badge
🛡️ Home team badge
🛡️ Away team badge
🏠 Native Home Assistant entities
🧩 HACS compatible
📦 Installation
HACS

The recommended way to install My Team is through HACS.

Add My Team as a custom repository
Open HACS in Home Assistant.
Go to Integrations.
Open the three-dot menu in the top-right.
Select Custom repositories.
Add the following repository:
https://github.com/Mkhimer69/My-Team

Select Integration as the category.
Click Add.
Search for My Team.
Install the integration.
Restart Home Assistant.

After restarting Home Assistant:

Settings → Devices & Services → Add Integration → My Team

🛠️ Manual Installation

Download or clone this repository and copy the integration into your Home Assistant configuration directory.

The integration must be located at:

/config/custom_components/sports_team_tracker/


The folder structure should look like:

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


Restart Home Assistant after installation.

Note: sports_team_tracker is the internal Home Assistant domain. The user-facing integration name is My Team.

⚙️ Configuration

My Team uses Home Assistant's configuration flow, so no YAML configuration is required.

Go to:

Settings → Devices & Services → Add Integration

Search for:

My Team


Enter the name of the football team you want to track.

My Team searches TheSportsDB and presents matching teams for you to select.

Once you select a team, the integration creates the required Home Assistant entities automatically.

You can add multiple teams.

For example:

⚽ Al Ahly
⚽ Zamalek
⚽ Liverpool
⚽ Barcelona
⚽ Trabzonspor


Each team is configured independently.

📡 Sensors

Each configured team provides two sensors.

⚽ Next Match

The Next Match sensor contains information about the team's next upcoming fixture.

Example:

sensor.al_ahly_next_match


State:

Al Ahly vs Smouha


The sensor also exposes detailed match information through its attributes.

Available attributes
Attribute	Description
event_id	Unique event ID
league	Competition / league name
season	Competition season
home_team	Home team
away_team	Away team
home_team_id	Home team ID
away_team_id	Away team ID
date	Match date
api_time_utc	Match time supplied by TheSportsDB
local_time	Match time in the Home Assistant timezone
venue	Stadium / venue
city	Match city
country	Match country
status	Match status
postponed	Whether the match is postponed
league_badge	League badge URL
home_team_badge	Home team badge URL
away_team_badge	Away team badge URL

Example:

league: Egyptian Premier League
season: 2026-2027
home_team: Al Ahly
away_team: Smouha
date: 2026-09-03
local_time: 20:00:00
venue: Cairo International Stadium
status: NS
postponed: no

🕒 Match Time

The Match Time sensor provides the kickoff time of the next match as a Home Assistant timestamp.

Example:

sensor.al_ahly_match_time


Example state:

2026-09-03T17:00:00+00:00


The sensor uses Home Assistant's:

device_class: timestamp


This makes it especially useful for automations and time-based cards.

For example:

triggers:
  - trigger: time
    at: sensor.al_ahly_match_time


You can use the timestamp sensor for:

⏰ Match reminders
📺 TV notifications
📱 Mobile notifications
📅 Dashboard cards
⏳ Countdown calculations
⚽ Match-day automations
🎨 Dashboard Example

The Next Match sensor exposes the league and team badge URLs, making it possible to create rich football dashboards directly from Home Assistant.

For example:

type: markdown
content: >
  {% set sensors = [
    'sensor.al_ahly_next_match',
    'sensor.barcelona_next_match',
    'sensor.liverpool_next_match',
    'sensor.zamalek_next_match_2'
  ] %}

  {% for sensor in sensors %}
  {% if states(sensor) != 'unknown' and
        state_attr(sensor, 'home_team') != None %}

  <div align="center">
    <img src="{{ state_attr(sensor, 'league_badge') }}" height="52">
    <sub>{{ state_attr(sensor, 'league') }}</sub>
  </div>

  <table width="100%">
    <tr>

      <td width="40%" align="center">
        <img
          src="{{ state_attr(sensor, 'home_team_badge') }}"
          height="60"
        >
        <br>
        <b>{{ state_attr(sensor, 'home_team') }}</b>
      </td>

      <td width="20%" align="center">
        <h2>
          {{ state_attr(sensor, 'local_time')[:5] }}
        </h2>

        <sub>
          {{ as_timestamp(
            strptime(
              state_attr(sensor, 'date'),
              '%Y-%m-%d',
              now()
            )
          ) | timestamp_custom('%d %b') }}
        </sub>
      </td>

      <td width="40%" align="center">
        <img
          src="{{ state_attr(sensor, 'away_team_badge') }}"
          height="60"
        >
        <br>
        <b>{{ state_attr(sensor, 'away_team') }}</b>
      </td>

    </tr>
  </table>

  {% if not loop.last %}
  <hr>
  {% endif %}

  {% endif %}
  {% endfor %}


This allows multiple teams to be displayed in a single card while automatically using:

🏆 League badge
🛡️ Home team badge
🛡️ Away team badge
🕒 Local kickoff time
📅 Match date
🏆 Competition name
🤖 Automations

The Match Time sensor can be used directly with Home Assistant automations.

For example, a reminder at kickoff:

triggers:
  - trigger: time
    at: sensor.zamalek_match_time

actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "⚽ Match Started"
      message: >
        {{ state_attr(
          'sensor.zamalek_next_match',
          'home_team'
        ) }}
        vs
        {{ state_attr(
          'sensor.zamalek_next_match',
          'away_team'
        ) }}


You can also use the timestamp to create your own pre-match reminders.

📺 TV Notifications

My Team works particularly well with TV notification integrations.

The badge URLs exposed by Next Match can be used as notification artwork.

Example:

action: notify.android_tv_fire_tv_192_168_1_7
data:
  title: "⚽ Match Center"
  message: >
    🏆 {{ state_attr(
      'sensor.al_ahly_next_match',
      'league'
    ) }}

    🏠 {{ state_attr(
      'sensor.al_ahly_next_match',
      'home_team'
    ) }}

    ⚔️ VS

    ✈️ {{ state_attr(
      'sensor.al_ahly_next_match',
      'away_team'
    ) }}

    🕒 {{ state_attr(
      'sensor.al_ahly_next_match',
      'local_time'
    )[:5] }}
  data:
    image: >
      {{ state_attr(
        'sensor.al_ahly_next_match',
        'league_badge'
      ) }}


Because each team has its own sensors, you can create a single automation that monitors all your favorite teams.

🔄 Data Updates

My Team periodically checks TheSportsDB for the latest fixture information.

The integration currently refreshes its data every 3 hours.

When a match has passed, the integration automatically moves on to the next available fixture.

This means your dashboard and automations can continue using the same sensors without manually changing the match.

🌐 Data Source

My Team uses TheSportsDB for football data.

TheSportsDB provides the fixture, team, competition, and badge information used by the integration.

Please refer to TheSportsDB for information regarding their API, data availability, and terms of use.

🐛 Troubleshooting
My Team doesn't appear in HACS

Make sure the repository has been added as a custom repository:

https://github.com/Mkhimer69/My-Team


with the category:

Integration


After installation, restart Home Assistant.

No team is found

Try searching using the team's common or official name.

For example:

Al Ahly
Zamalek
Liverpool
Barcelona
Trabzonspor


The available search results depend on the data provided by TheSportsDB.

No upcoming match is shown

A team may not have an upcoming fixture available.

Possible reasons include:

No upcoming fixture has been published.
The competition schedule is not yet available.
The fixture has not yet been added to TheSportsDB.
The upstream data is temporarily unavailable.
Match information is incorrect or outdated

Football fixtures can change.

Kickoff times, venues, competitions, and match status may be updated after a fixture is initially published.

My Team periodically refreshes the data from TheSportsDB.

Team badges are missing

Team and league artwork is provided by TheSportsDB.

If a badge is missing, the corresponding artwork may not currently be available from the data provider.

🧩 Technical Information

The Home Assistant integration domain is:

sports_team_tracker


The user-facing integration name is:

My Team


The integration uses Home Assistant's configuration flow and cloud polling architecture.

❤️ Contributing

Contributions, suggestions, and bug reports are welcome.

If you find a problem, please open an issue on GitHub and include:

Home Assistant version
My Team version
Team being tracked
Affected match
Relevant Home Assistant logs

Please remove personal or sensitive information from logs before sharing them.

📜 License

See the LICENSE file in this repository for licensing information.

⭐ Support the Project

If My Team is useful in your Home Assistant setup, consider giving the project a ⭐ on GitHub.

It helps other Home Assistant users discover the integration and supports continued development.

⚽ My Team

Your teams. Your matches. Your Home Assistant.

:::

I would **not add screenshots yet**. First, let's get the README and repository structure correct. Then we can add a polished screenshot/GIF of your actual dashboard — that will make the project much more convincing than generic screenshots.

One other thing: I deliberately used **`My Team` everywhere users see the integration**, while retaining `sports_team_tracker` only where Home Assistant's internal domain/path matters. That's the distinction we want.
