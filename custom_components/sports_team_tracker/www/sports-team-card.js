/**
 * My Team — match-day card for the My Team integration.
 *
 * Shipped inside the integration: no Mushroom, no card-mod, no YAML template to
 * copy. Add it as `custom:sports-team-card` and pick a team's "Next match"
 * entity; the card renders the league badge, the fixture, the kickoff and a
 * live countdown, and flips to LIVE NOW at kickoff.
 *
 * Config:
 *   entity: sensor.<team>_next_match   (required)
 *   accent: "#43a047"                  (optional left border colour)
 *   show_venue: true                   (optional, default true)
 */

const ACCENT_DEFAULT = '#43a047';

class SportsTeamCard extends HTMLElement {
  static getStubConfig(hass) {
    const entity = Object.keys(hass.states).find(
      id => id.startsWith('sensor.') && id.endsWith('_next_match')
    );
    return { entity: entity || '' };
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error('My Team card: set an entity (a team’s Next match sensor)');
    }
    this._config = {
      accent: ACCENT_DEFAULT,
      show_venue: true,
      ...config
    };
    this._built = false;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
    this._startTicker();
  }

  getCardSize() {
    return 1;
  }

  connectedCallback() {
    this._startTicker();
  }

  disconnectedCallback() {
    if (this._timer) {
      clearInterval(this._timer);
      this._timer = null;
    }
  }

  _startTicker() {
    if (this._timer) return;
    // a 10s tick keeps the countdown honest and flips LIVE NOW promptly
    this._timer = setInterval(() => this._render(), 10000);
  }

  _build() {
    this.attachShadow({ mode: 'open' });
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card {
          border-left: 3px solid var(--sports-accent, #43a047);
          border-radius: 12px;
          padding: 12px 14px;
          display: flex;
          align-items: center;
          gap: 12px;
          cursor: pointer;
          overflow: hidden;
        }
        .badge {
          width: 52px;
          height: 52px;
          flex: 0 0 52px;
          object-fit: contain;
        }
        .badge.empty { opacity: .25; }
        .body { min-width: 0; flex: 1 1 auto; }
        .primary {
          font-size: 15px;
          font-weight: 600;
          line-height: 1.3;
          color: var(--primary-text-color);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .secondary {
          font-size: 13px;
          color: var(--secondary-text-color);
          line-height: 1.4;
          margin-top: 2px;
        }
        .meta {
          font-size: 11.5px;
          color: var(--secondary-text-color);
          opacity: .8;
          margin-top: 2px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .live { color: #e53935; font-weight: 700; }
      </style>
      <ha-card>
        <img class="badge empty" alt="" />
        <div class="body">
          <div class="primary">—</div>
          <div class="secondary">no data</div>
          <div class="meta"></div>
        </div>
      </ha-card>
    `;
    this._built = true;
  }

  _render() {
    if (!this._built) this._build();
    if (!this._hass || !this._config) return;

    const card = this.shadowRoot.querySelector('ha-card');
    const badge = this.shadowRoot.querySelector('.badge');
    const primary = this.shadowRoot.querySelector('.primary');
    const secondary = this.shadowRoot.querySelector('.secondary');
    const meta = this.shadowRoot.querySelector('.meta');

    card.style.setProperty('--sports-accent', this._config.accent);
    card.onclick = () => {
      this.dispatchEvent(new CustomEvent('hass-more-info', {
        bubbles: true,
        composed: true,
        detail: { entityId: this._config.entity }
      }));
    };

    const state = this._hass.states[this._config.entity];
    if (!state) {
      primary.textContent = this._config.entity;
      secondary.textContent = 'entity not found';
      meta.textContent = '';
      badge.removeAttribute('src');
      badge.classList.add('empty');
      return;
    }

    const a = state.attributes || {};
    const unavailable = ['unknown', 'unavailable'].includes(state.state);

    primary.textContent = unavailable
      ? 'Next match'
      : `${a.home_team || state.state.split(' vs ')[0] || '—'} vs ${a.away_team || state.state.split(' vs ')[1] || ''}`.trim();

    const kickoff = this._kickoff(a);
    secondary.textContent = unavailable ? 'no data' : this._when(kickoff, a);

    const bits = [];
    if (a.league) bits.push(a.league);
    if (this._config.show_venue && a.venue) bits.push(a.venue);
    if (a.city) bits.push(a.city);
    meta.textContent = bits.join(' · ');

    const picture = a.league_badge || '';
    if (picture) {
      badge.src = picture;
      badge.classList.remove('empty');
    } else {
      badge.removeAttribute('src');
      badge.classList.add('empty');
    }
  }

  _kickoff(a) {
    const date = a.date;
    if (!date) return null;
    const time = (a.local_time || '00:00:00').slice(0, 8);
    const ts = Date.parse(`${date}T${time}`);
    return Number.isNaN(ts) ? null : ts;
  }

  _when(ts, a) {
    const clock = (a.local_time || '').slice(0, 5);
    if (!ts) return clock || 'time to be confirmed';

    const diff = Math.round((ts - Date.now()) / 1000);
    if (diff < 0) return `🔴 LIVE NOW${clock ? ` · kicked off ${clock}` : ''}`;

    const day = diff < 86400 ? 'Today'
      : diff < 172800 ? 'Tomorrow'
        : new Date(ts).toLocaleDateString(undefined, { weekday: 'short', day: '2-digit', month: 'short' });

    const d = Math.floor(diff / 86400);
    const h = Math.floor((diff % 86400) / 3600);
    const m = Math.floor((diff % 3600) / 60);
    const inBits = [d ? `${d}d` : '', h ? `${h}h` : '', `${m}m`].filter(Boolean).join(' ');

    return `${day}${clock ? ` · ${clock}` : ''} · in ${inBits}`;
  }
}

if (!customElements.get('sports-team-card')) {
  customElements.define('sports-team-card', SportsTeamCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === 'sports-team-card')) {
  window.customCards.push({
    type: 'sports-team-card',
    name: 'My Team Match',
    description: 'League badge, fixture, kickoff and a live countdown for a team tracked by My Team.',
    preview: true,
    documentationURL: 'https://github.com/Mkhimer69/My-Team#-add-the-card'
  });
}
