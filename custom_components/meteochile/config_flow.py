"""Flujo de configuración: Región → Localidad → Estación para la temperatura actual."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import MeteoChileClient, MeteoChileData, MeteoChileError
from .const import (
    CONF_CITY,
    CONF_CITY_NAME,
    CONF_REGION,
    CONF_STATION,
    DEFAULT_STATION_BY_CITY,
    DEFAULT_STATION_BY_REGION,
    DOMAIN,
    NO_STATION,
    REGIONS,
    STATIONS,
)
from .coordinator import MeteoChileConfigEntry

_LOGGER = logging.getLogger(__name__)


def _dropdown(options: list[SelectOptionDict]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)
    )


def _region_options(data: MeteoChileData) -> list[SelectOptionDict]:
    present = {city.region for city in data.forecasts.values()}
    ordered = [code for code in REGIONS if code in present]
    ordered += sorted(present - set(REGIONS))
    return [SelectOptionDict(value=code, label=REGIONS.get(code, code)) for code in ordered]


def _city_options(data: MeteoChileData, region: str) -> list[SelectOptionDict]:
    # Se respeta el orden del archivo de la DMC (aprox. norte → sur).
    return [
        SelectOptionDict(value=city.key, label=city.name)
        for city in data.forecasts.values()
        if city.region == region
    ]


def _station_options(data: MeteoChileData) -> list[SelectOptionDict]:
    options = [
        SelectOptionDict(
            value=code,
            label=f"{STATIONS[code]} · {code}" if code in STATIONS else code,
        )
        for code in data.stations
    ]
    options.sort(key=lambda opt: opt["label"])
    options.append(
        SelectOptionDict(value=NO_STATION, label="Sin estación (solo pronóstico)")
    )
    return options


def suggested_station(data: MeteoChileData, region: str, city: str) -> str:
    """Estación sugerida para una localidad."""
    for candidate in (
        DEFAULT_STATION_BY_CITY.get(city),
        DEFAULT_STATION_BY_REGION.get(region),
    ):
        if candidate and candidate in data.stations:
            return candidate
    return NO_STATION


class MeteoChileConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configuración de una localidad de MeteoChile."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: MeteoChileData | None = None
        self._region: str | None = None
        self._city: str | None = None

    async def _async_load(self) -> MeteoChileData:
        if self._data is None:
            client = MeteoChileClient(async_get_clientsession(self.hass))
            self._data = await client.async_get_data()
        return self._data

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Paso 1: región."""
        errors: dict[str, str] = {}
        try:
            data = await self._async_load()
        except MeteoChileError as err:
            _LOGGER.warning("No se pudo conectar con la DMC: %s", err)
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="user", data_schema=vol.Schema({}), errors=errors
            )

        if user_input is not None:
            self._region = user_input[CONF_REGION]
            return await self.async_step_city()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_REGION): _dropdown(_region_options(data))}
            ),
            errors=errors,
        )

    async def async_step_city(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Paso 2: localidad dentro de la región."""
        assert self._data is not None and self._region is not None

        if user_input is not None:
            self._city = user_input[CONF_CITY]
            await self.async_set_unique_id(self._city)
            self._abort_if_unique_id_configured()
            return await self.async_step_station()

        return self.async_show_form(
            step_id="city",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CITY): _dropdown(
                        _city_options(self._data, self._region)
                    )
                }
            ),
            description_placeholders={
                "region": REGIONS.get(self._region, self._region)
            },
        )

    async def async_step_station(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Paso 3: estación para temperatura y condición actual."""
        assert self._data is not None and self._region and self._city
        city = self._data.forecasts[self._city]

        if user_input is not None:
            return self.async_create_entry(
                title=city.name,
                data={
                    CONF_REGION: self._region,
                    CONF_CITY: self._city,
                    CONF_CITY_NAME: city.name,
                },
                options={CONF_STATION: user_input[CONF_STATION]},
            )

        default = suggested_station(self._data, self._region, self._city)
        return self.async_show_form(
            step_id="station",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_STATION, default=default): _dropdown(
                        _station_options(self._data)
                    )
                }
            ),
            description_placeholders={"city": city.name},
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: MeteoChileConfigEntry) -> OptionsFlow:
        """Opciones: cambiar la estación."""
        return MeteoChileOptionsFlow()


class MeteoChileOptionsFlow(OptionsFlow):
    """Permite cambiar la estación de la temperatura actual."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        coordinator = self.config_entry.runtime_data
        data = coordinator.data
        current = self.config_entry.options.get(
            CONF_STATION,
            suggested_station(
                data,
                self.config_entry.data[CONF_REGION],
                self.config_entry.data[CONF_CITY],
            ),
        )
        options = _station_options(data)
        if current not in {opt["value"] for opt in options}:
            options.insert(0, SelectOptionDict(value=current, label=f"{current} (sin datos ahora)"))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {vol.Required(CONF_STATION, default=current): _dropdown(options)}
            ),
        )
