"""Constantes de la integración MeteoChile (DMC)."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "meteochile"

BASE_URL: Final = "https://archivos.meteochile.gob.cl/portaldmc"
URL_FORECAST: Final = f"{BASE_URL}/meteochile/js/pronostico.js"
URL_CURRENT: Final = f"{BASE_URL}/appdata/condicionactual.js"
URL_UV: Final = f"{BASE_URL}/appdata/pronostico_radiacion_uv.js"

ATTRIBUTION: Final = "Datos: Dirección Meteorológica de Chile (meteochile.gob.cl)"
MANUFACTURER: Final = "Dirección Meteorológica de Chile"
TIMEZONE: Final = "America/Santiago"

# La DMC publica las observaciones de cada estación una vez por hora (METAR)
# y regenera condicionactual.js unos minutos después (~hh:12, hh:33, hh:51).
# Se revisa ese archivo (pequeño, ~4 KB) cada 5 minutos para mostrar el dato
# nuevo poco después de publicado; el pronóstico cambia 1-2 veces al día.
UPDATE_INTERVAL: Final = timedelta(minutes=5)
FORECAST_INTERVAL: Final = timedelta(minutes=30)
REQUEST_TIMEOUT: Final = 20

CONF_REGION: Final = "region"
CONF_CITY: Final = "city"
CONF_CITY_NAME: Final = "city_name"
CONF_STATION: Final = "station"

NO_STATION: Final = "none"

# Códigos de región que usa el portal de la DMC (orden norte → sur).
REGIONS: Final[dict[str, str]] = {
    "01a": "Región de Arica y Parinacota",
    "01b": "Región de Tarapacá",
    "02": "Región de Antofagasta",
    "03": "Región de Atacama",
    "04": "Región de Coquimbo",
    "05": "Región de Valparaíso",
    "05m": "Región Metropolitana de Santiago",
    "06": "Región del Libertador General Bernardo O'Higgins",
    "07": "Región del Maule",
    "08a": "Región de Ñuble",
    "08b": "Región del Biobío",
    "09": "Región de La Araucanía",
    "10a": "Región de Los Ríos",
    "10b": "Región de Los Lagos",
    "11": "Región de Aysén",
    "12": "Región de Magallanes y de la Antártica Chilena",
    "ip": "Isla de Pascua",
    "jf": "Archipiélago Juan Fernández",
    "an": "Península Antártica",
}

# Estaciones (aeródromos, código OACI) publicadas en condicionactual.js.
# Las que no estén aquí se muestran solo con su código.
STATIONS: Final[dict[str, str]] = {
    "SCAR": "Arica (Chacalluta)",
    "SCDA": "Iquique (Diego Aracena)",
    "SCCF": "Calama (El Loa)",
    "SCFA": "Antofagasta (Cerro Moreno)",
    "SCAT": "Copiapó/Caldera (Desierto de Atacama)",
    "SCSE": "La Serena (La Florida)",
    "SCVM": "Viña del Mar (Torquemada)",
    "SCRD": "Viña del Mar (Rodelillo)",
    "SCSN": "Santo Domingo",
    "SCEL": "Santiago (Pudahuel)",
    "SCTB": "Santiago (Tobalaba)",
    "SCQN": "Santiago (Quinta Normal)",
    "SCRG": "Rancagua (La Independencia)",
    "SCIC": "Curicó (General Freire)",
    "SCCH": "Chillán (Bernardo O'Higgins)",
    "SCIE": "Concepción (Carriel Sur)",
    "SCGE": "Los Ángeles (María Dolores)",
    "SCQP": "Temuco (La Araucanía)",
    "SCVD": "Valdivia (Pichoy)",
    "SCJO": "Osorno (Cañal Bajo)",
    "SCTE": "Puerto Montt (El Tepual)",
    "SCTN": "Chaitén",
    "SCFT": "Futaleufú",
    "SCAS": "Puerto Aysén",
    "SCCY": "Coyhaique (Teniente Vidal)",
    "SCBA": "Balmaceda",
    "SCCC": "Chile Chico",
    "SCHR": "Cochrane",
    "SCNT": "Puerto Natales",
    "SCCI": "Punta Arenas (Carlos Ibáñez del Campo)",
    "SCFM": "Porvenir",
    "SCGZ": "Puerto Williams",
    "SCIP": "Isla de Pascua (Mataveri)",
    "SCIR": "Juan Fernández (Robinson Crusoe)",
    "SCRM": "Antártica (Teniente Marsh)",
}

# Estación sugerida por región para la "temperatura actual".
DEFAULT_STATION_BY_REGION: Final[dict[str, str]] = {
    "01a": "SCAR",
    "01b": "SCDA",
    "02": "SCFA",
    "03": "SCAT",
    "04": "SCSE",
    "05": "SCVM",
    "05m": "SCQN",
    "06": "SCRG",
    "07": "SCIC",
    "08a": "SCCH",
    "08b": "SCIE",
    "09": "SCQP",
    "10a": "SCVD",
    "10b": "SCTE",
    "11": "SCBA",
    "12": "SCCI",
    "ip": "SCIP",
    "jf": "SCIR",
    "an": "SCRM",
}

# Ajustes finos por localidad (índice del pronóstico → estación).
DEFAULT_STATION_BY_CITY: Final[dict[str, str]] = {
    "calama": "SCCF",
    "snpedro": "SCCF",
    "ollague": "SCCF",
    "snantonio": "SCSN",
    "snantonioi": "SCSN",
    "algarrobo": "SCSN",
    "colina": "SCEL",
    "stgop": "SCEL",
    "curacavi": "SCEL",
    "melipilla": "SCEL",
    "stgoo": "SCTB",
    "snjosemaipo": "SCTB",
    "angeles": "SCGE",
    "osorno": "SCJO",
    "chaiten": "SCTN",
    "futaleufu": "SCFT",
    "coyhaique": "SCCY",
    "aysen": "SCAS",
    "chchico": "SCCC",
    "cochrane": "SCHR",
    "natales": "SCNT",
    "torres": "SCNT",
    "porvenir": "SCFM",
    "pwilliams": "SCGZ",
}

# Tramos del día en el pronóstico de la DMC.
PERIODS: Final = ("madrugada", "mañana", "tarde", "noche")
