"""Registro de la tarjeta MeteoChile (Lovelace) en el frontend de Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from ..const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "meteochile-card.js"
URL_BASE = f"/{DOMAIN}"
CARD_URL = f"{URL_BASE}/{CARD_FILENAME}"
_DATA_KEY = f"{DOMAIN}_frontend_registered"


async def async_register_card(hass: HomeAssistant, version: str) -> None:
    """Sirve el JS de la tarjeta y lo agrega a todas las páginas del frontend."""
    if hass.data.get(_DATA_KEY):
        return
    if getattr(hass, "http", None) is None:
        _LOGGER.debug("HTTP no disponible: no se registra la tarjeta")
        return

    path = Path(__file__).parent / CARD_FILENAME
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL, str(path), cache_headers=False)]
    )
    # El parámetro de versión evita que el navegador use una copia vieja.
    add_extra_js_url(hass, f"{CARD_URL}?v={version}")
    hass.data[_DATA_KEY] = True
    _LOGGER.debug("Tarjeta MeteoChile registrada en %s", CARD_URL)
