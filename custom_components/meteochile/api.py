"""Cliente para los archivos públicos de la DMC."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging

import aiohttp

from .const import REQUEST_TIMEOUT, URL_CURRENT, URL_FORECAST, URL_UV
from .parser import (
    CityForecast,
    StationObservation,
    decode_bytes,
    parse_current,
    parse_forecast,
    parse_uv,
)

_LOGGER = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "HomeAssistant-MeteoChile/1.0 (+https://www.home-assistant.io)",
    "Referer": "https://www.meteochile.gob.cl/",
}


class MeteoChileError(Exception):
    """No fue posible obtener o leer los datos de la DMC."""


@dataclass(slots=True)
class MeteoChileData:
    """Datos completos descargados en una actualización."""

    forecasts: dict[str, CityForecast]
    stations: dict[str, StationObservation] = field(default_factory=dict)
    stations_updated: str | None = None
    uv: dict[str, float] = field(default_factory=dict)


class MeteoChileClient:
    """Descarga y procesa pronostico.js, condicionactual.js y el índice UV."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get(self, url: str) -> str:
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.get(url, headers=_HEADERS) as resp:
                    resp.raise_for_status()
                    return decode_bytes(await resp.read())
        except (TimeoutError, aiohttp.ClientError) as err:
            raise MeteoChileError(f"Error al descargar {url}: {err}") from err

    async def async_get_forecast(self) -> tuple[dict[str, CityForecast], dict[str, float]]:
        """Pronóstico (obligatorio) e índice UV (opcional)."""
        forecast_txt, uv_txt = await asyncio.gather(
            self._get(URL_FORECAST), self._get(URL_UV), return_exceptions=True
        )
        if isinstance(forecast_txt, BaseException):
            raise MeteoChileError(str(forecast_txt)) from forecast_txt
        forecasts = parse_forecast(forecast_txt)
        if not forecasts:
            raise MeteoChileError("El archivo de pronóstico no trae localidades")
        uv: dict[str, float] = {}
        if isinstance(uv_txt, BaseException):
            _LOGGER.debug("Sin índice UV: %s", uv_txt)
        else:
            uv = parse_uv(uv_txt)
        return forecasts, uv

    async def async_get_current(self) -> tuple[dict[str, StationObservation], str | None]:
        """Observaciones actuales de las estaciones."""
        return parse_current(await self._get(URL_CURRENT))

    async def async_get_data(self) -> MeteoChileData:
        """Descarga todo. Solo el pronóstico es obligatorio."""
        forecasts, uv = await self.async_get_forecast()
        data = MeteoChileData(forecasts=forecasts, uv=uv)
        try:
            data.stations, data.stations_updated = await self.async_get_current()
        except MeteoChileError as err:
            _LOGGER.debug("Sin condición actual: %s", err)
        return data
