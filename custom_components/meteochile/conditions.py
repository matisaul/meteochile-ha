"""Traducción de los textos e íconos de la DMC a condiciones de Home Assistant."""

from __future__ import annotations

import re

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_HAIL,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
    ATTR_CONDITION_WINDY_VARIANT,
)

# Mayor valor = condición más relevante al resumir varios tramos del día.
SEVERITY: dict[str, int] = {
    ATTR_CONDITION_SUNNY: 0,
    ATTR_CONDITION_CLEAR_NIGHT: 0,
    ATTR_CONDITION_PARTLYCLOUDY: 1,
    ATTR_CONDITION_CLOUDY: 2,
    ATTR_CONDITION_WINDY: 3,
    ATTR_CONDITION_WINDY_VARIANT: 3,
    ATTR_CONDITION_FOG: 4,
    ATTR_CONDITION_RAINY: 6,
    ATTR_CONDITION_POURING: 7,
    ATTR_CONDITION_SNOWY: 7,
    ATTR_CONDITION_SNOWY_RAINY: 7,
    ATTR_CONDITION_HAIL: 8,
    ATTR_CONDITION_LIGHTNING_RAINY: 9,
}

_ICON_MAP: tuple[tuple[str, str], ...] = (
    ("tormenta", ATTR_CONDITION_LIGHTNING_RAINY),
    ("granizo", ATTR_CONDITION_HAIL),
    ("aguanieve", ATTR_CONDITION_SNOWY_RAINY),
    ("nieve", ATTR_CONDITION_SNOWY),
    ("chubasco", ATTR_CONDITION_RAINY),
    ("llovizna", ATTR_CONDITION_RAINY),
    ("lluvia", ATTR_CONDITION_RAINY),
    ("niebla", ATTR_CONDITION_FOG),
    ("neblina", ATTR_CONDITION_FOG),
    ("viento", ATTR_CONDITION_WINDY),
    ("cubierto", ATTR_CONDITION_CLOUDY),
    ("parcialalta", ATTR_CONDITION_PARTLYCLOUDY),
    ("pocasnubes", ATTR_CONDITION_PARTLYCLOUDY),
    ("parcial", ATTR_CONDITION_CLOUDY),  # en la DMC "parcial.png" = "Nublado"
    ("nublado", ATTR_CONDITION_CLOUDY),
    ("despejado", ATTR_CONDITION_SUNNY),
)

_STRONG_WIND_RE = re.compile(r"viento (?:entre|sobre|de) ([4-9]\d|\d{3})")


def _from_text(text: str) -> str | None:
    """Condición a partir del texto (se usa la primera parte de 'X variando a Y')."""
    text = text.lower()
    main = text.split("variando a")[0]
    whole = text

    if "tormenta" in whole or "eléctrica" in whole or "electrica" in whole:
        return ATTR_CONDITION_LIGHTNING_RAINY
    if "granizo" in whole:
        return ATTR_CONDITION_HAIL
    if "nieve" in main or "nevadas" in main:
        if "lluvia" in main or "precipitac" in main:
            return ATTR_CONDITION_SNOWY_RAINY
        return ATTR_CONDITION_SNOWY
    if "lluvia intensa" in main or "lluvia fuerte" in main or "temporal" in main:
        return ATTR_CONDITION_POURING
    if any(word in main for word in ("lluvia", "llovizna", "chubasco", "precipitac")):
        return ATTR_CONDITION_RAINY
    if any(word in main for word in ("niebla", "neblina", "bruma")):
        return ATTR_CONDITION_FOG

    cloudy = "cubierto" in main or (
        "nublado" in main and "parcial" not in main
    )
    if _STRONG_WIND_RE.search(main):
        return ATTR_CONDITION_WINDY_VARIANT if cloudy else ATTR_CONDITION_WINDY
    if cloudy:
        return ATTR_CONDITION_CLOUDY
    if any(word in main for word in ("nubosidad parcial", "escasa nubosidad", "parcial")):
        return ATTR_CONDITION_PARTLYCLOUDY
    if "despejado" in main:
        return ATTR_CONDITION_SUNNY
    return None


def _from_icon(icon: str) -> str | None:
    icon = icon.lower()
    if not icon:
        return None
    for key, condition in _ICON_MAP:
        if key in icon:
            if condition == ATTR_CONDITION_WINDY:
                # El ícono de viento no dice nada de nubes: mejor el texto.
                return None
            return condition
    return None


def to_condition(text: str | None, icon: str | None, night: bool = False) -> str | None:
    """Devuelve la condición de Home Assistant para un tramo."""
    icon = icon or ""
    condition = _from_text(text or "") or _from_icon(icon)
    if condition is None:
        return None
    is_night = night or "noche" in icon.lower()
    if condition == ATTR_CONDITION_SUNNY and is_night:
        return ATTR_CONDITION_CLEAR_NIGHT
    if condition == ATTR_CONDITION_CLEAR_NIGHT and not is_night:
        return ATTR_CONDITION_SUNNY
    return condition


def worst(conditions: list[str | None]) -> str | None:
    """La condición más relevante de una lista (ej. mañana + tarde)."""
    valid = [c for c in conditions if c]
    if not valid:
        return None
    return max(valid, key=lambda c: SEVERITY.get(c, 0))
