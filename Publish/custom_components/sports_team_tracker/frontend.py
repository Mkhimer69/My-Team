"""Serve the My Team card and register it as a dashboard resource.

The card lives in ``www/sports-team-card.js`` inside the integration, so it
travels with the integration: installing or updating My Team through HACS also
installs the card. Registration is idempotent and every step is best-effort —
a Home Assistant build that cannot register a resource must never fail the
integration setup over a card, so the failure is logged with the manual step.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CARD_URL = "/sports_team_tracker/sports-team-card.js"
CARD_FILE = Path(__file__).parent / "www" / "sports-team-card.js"
_SETUP_FLAG = "sports_team_tracker_frontend"


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Serve the card file and add it to the dashboard resources once."""
    if hass.data.get(_SETUP_FLAG):
        return
    hass.data[_SETUP_FLAG] = True

    served = await _async_serve(hass)
    if not served:
        return
    await _async_register_resource(hass)


async def _async_serve(hass: HomeAssistant) -> bool:
    """Expose the card on the Home Assistant HTTP server."""
    if not CARD_FILE.is_file():
        _LOGGER.warning("My Team card file is missing: %s", CARD_FILE)
        return False

    try:
        from homeassistant.components.http import StaticPathConfig

        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, str(CARD_FILE), False)]
        )
        return True
    except ImportError:
        pass
    except Exception as err:  # noqa: BLE001 - never break setup over a card
        _LOGGER.warning("My Team could not serve its card (%s)", err)
        return False

    # Home Assistant older than 2024.7
    try:
        hass.http.register_static_path(CARD_URL, str(CARD_FILE), False)
        return True
    except Exception as err:  # noqa: BLE001
        _LOGGER.warning("My Team could not serve its card (%s)", err)
        return False


async def _async_register_resource(hass: HomeAssistant) -> None:
    """Add the card as a Lovelace resource when dashboards live in storage."""
    manual = (
        "Add it by hand: Settings → Dashboards → ⋮ → Resources → Add resource, "
        "URL %s, type JavaScript module." % CARD_URL
    )
    try:
        from homeassistant.components.lovelace.const import LOVELACE_DATA

        lovelace = hass.data.get(LOVELACE_DATA)
        resources = getattr(lovelace, "resources", None)
        if resources is None:
            _LOGGER.info("My Team card is served but not registered. %s", manual)
            return

        for item in resources.async_items():
            if item.get("url") == CARD_URL:
                return

        await resources.async_create_item({"res_type": "module", "url": CARD_URL})
        _LOGGER.debug("My Team card registered as a dashboard resource")
    except Exception as err:  # noqa: BLE001
        _LOGGER.info("My Team card was not registered automatically (%s). %s", err, manual)
