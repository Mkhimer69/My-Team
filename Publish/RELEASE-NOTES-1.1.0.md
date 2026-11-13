## My Team 1.1.0 — the card ships with the integration

No more copying YAML. My Team now brings its own match card.

### 🃏 A card that comes with it

`custom:sports-team-card` — league badge, `Home vs Away`, kickoff and a live
countdown that flips to **🔴 LIVE NOW** at kickoff. No Mushroom, no card-mod, no
template to paste.

1. Edit a dashboard → **Add card** → search **My Team Match**
2. Pick the team's `Next match` sensor
3. Save

The integration serves the card at `/sports_team_tracker/sports-team-card.js` and
registers it as a dashboard resource the first time it loads. If your dashboard
is YAML-mode, add that URL once as a **JavaScript module** (Settings → Dashboards
→ ⋮ → Resources) and the card still works the same way.

Options:

```yaml
type: custom:sports-team-card
entity: sensor.zamalek_next_match_2
accent: "#43a047"   # left border colour, optional
show_venue: true    # optional
```

### ✅ Also in this release

- **One version number.** `manifest.json` said `0.3.0` while the integration said
  `1.0.0`; Home Assistant and HACS now show `1.1.0` everywhere.
- The Mushroom + card-mod dashboard stays fully supported if you already use it —
  the shipped card is an alternative, not a replacement.

### ⬆️ Upgrading

HACS → **My Team** → **Update**, then restart Home Assistant. Config entries,
sensors and automations are untouched; no reconfiguration needed.

### 🧩 Requirements

- Home Assistant with HACS
- `sports_team_tracker` custom repository added as category **Integration**
- Team data from TheSportsDB with an ESPN fallback — no extra keys or accounts
