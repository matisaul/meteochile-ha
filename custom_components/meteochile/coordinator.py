"""Coordinador de actualizaciones de MeteoChile."""

from __future__ import annotations

import logging
import time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MeteoChileClient, MeteoChileData, MeteoChileError
from .const import DOMAIN, FORECAST_INTERVAL, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type MeteoChileConfigEntry = ConfigEntry[MeteoChileCoordinator]


class MeteoChileCoordinator(DataUpdateCoordinator[MeteoChileData]):
    """Condición actual cada UPDATE_INTERVAL; pronóstico cada FORECAST_INTERVAL."""

    config_entry: MeteoChileConfigEntry

    def __init__(self, hass: HomeAssistant, entry: MeteoChileConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = MeteoChileClient(async_get_clientsession(hass))
        self._forecast_fetched: float | None = None

    def _forecast_due(self) -> bool:
        return (
            self.data is None
            or self._forecast_fetched is None
            or time.monotonic() - self._forecast_fetched
            >= FORECAST_INTERVAL.total_seconds()
        )

    async def _async_update_data(self) -> MeteoChileData:
        previous = self.data

        if self._forecast_due():
            try:
                forecasts, uv = await self.client.async_get_forecast()
                self._forecast_fetched = time.monotonic()
            except MeteoChileError as err:
                if previous is None:
                    raise UpdateFailed(str(err)) from err
                _LOGGER.debug("Pronóstico no disponible, se mantiene el anterior: %s", err)
                forecasts, uv = previous.forecasts, previous.uv
        else:
            forecasts, uv = previous.forecasts, previous.uv

        data = MeteoChileData(forecasts=forecasts, uv=uv)
        try:
            data.stations, data.stations_updated = await self.client.async_get_current()
        except MeteoChileError as err:
            _LOGGER.debug("Condición actual no disponible: %s", err)
            if previous is not None:
                data.stations = previous.stations
                data.stations_updated = previous.stations_updated
        return data
