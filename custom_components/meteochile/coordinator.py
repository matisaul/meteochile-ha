"""Coordinador de actualizaciones de MeteoChile."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MeteoChileClient, MeteoChileData, MeteoChileError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

type MeteoChileConfigEntry = ConfigEntry[MeteoChileCoordinator]


class MeteoChileCoordinator(DataUpdateCoordinator[MeteoChileData]):
    """Actualiza los datos de la DMC cada UPDATE_INTERVAL."""

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

    async def _async_update_data(self) -> MeteoChileData:
        try:
            return await self.client.async_get_data()
        except MeteoChileError as err:
            raise UpdateFailed(str(err)) from err
