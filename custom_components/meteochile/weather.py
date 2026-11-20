"""Entidad Weather de MeteoChile."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_SUNNY,
    Forecast,
    SingleCoordinatorWeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.const import UnitOfLength, UnitOfSpeed, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.sun import is_up
from homeassistant.util import dt as dt_util

from .conditions import to_condition, worst
from .const import (
    ATTRIBUTION,
    CONF_CITY,
    CONF_CITY_NAME,
    CONF_REGION,
    CONF_STATION,
    DOMAIN,
    MANUFACTURER,
    NO_STATION,
    PERIODS,
    REGIONS,
    STATIONS,
    TIMEZONE,
)
from .coordinator import MeteoChileConfigEntry, MeteoChileCoordinator
from .parser import CityForecast, DayForecast, StationObservation

TZ = ZoneInfo(TIMEZONE)

# Índices de los tramos en el pronóstico: 0 madrugada, 1 mañana, 2 tarde, 3 noche.
_DAY_PERIODS = (1, 2)
_NIGHT_PERIOD = 3


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MeteoChileConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crea la entidad weather de la localidad."""
    async_add_entities([MeteoChileWeather(entry.runtime_data, entry)])


def _period_condition(day: DayForecast, idx: int, night: bool) -> str | None:
    text = day.texts[idx] if idx < len(day.texts) else ""
    icon = day.icons[idx] if idx < len(day.icons) else ""
    if not text and not icon:
        return None
    return to_condition(text, icon, night=night)


def _day_condition(day: DayForecast) -> str | None:
    return worst([_period_condition(day, i, night=False) for i in _DAY_PERIODS])


def _night_condition(day: DayForecast) -> str | None:
    return _period_condition(day, _NIGHT_PERIOD, night=True)


def _base_date(city: CityForecast) -> datetime:
    try:
        day = datetime.strptime(city.base_date, "%Y-%m-%d").date()
    except ValueError:
        day = dt_util.now(TZ).date()
    return datetime.combine(day, time(0, 0), tzinfo=TZ)


def _current_period_index(now: datetime) -> int:
    hour = now.hour
    if hour < 6:
        return 0
    if hour < 12:
        return 1
    if hour < 20:
        return 2
    return 3


class MeteoChileWeather(SingleCoordinatorWeatherEntity[MeteoChileCoordinator]):
    """Clima actual y pronóstico de una localidad de la DMC."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_name = None
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_visibility_unit = UnitOfLength.KILOMETERS
    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_TWICE_DAILY
    )

    def __init__(
        self, coordinator: MeteoChileCoordinator, entry: MeteoChileConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._city_key: str = entry.data[CONF_CITY]
        self._region: str = entry.data[CONF_REGION]
        self._station_code: str = entry.options.get(CONF_STATION, NO_STATION)
        city_name = entry.data.get(CONF_CITY_NAME, self._city_key)

        self._attr_unique_id = f"{DOMAIN}_{self._city_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._city_key)},
            name=f"MeteoChile {city_name}",
            manufacturer=MANUFACTURER,
            model=REGIONS.get(self._region, self._region),
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.meteochile.gob.cl/",
        )

    # ------------------------------------------------------------------ datos

    @property
    def _city(self) -> CityForecast | None:
        return self.coordinator.data.forecasts.get(self._city_key)

    @property
    def _station(self) -> StationObservation | None:
        if self._station_code == NO_STATION:
            return None
        return self.coordinator.data.stations.get(self._station_code)

    @property
    def available(self) -> bool:
        return super().available and self._city is not None

    # ------------------------------------------------------------ condición actual

    @property
    def condition(self) -> str | None:
        station = self._station
        condition = None
        if station is not None:
            condition = to_condition(station.description, station.icon)
        if condition is None:
            condition = self._forecast_condition_now()
        if condition in (ATTR_CONDITION_SUNNY, ATTR_CONDITION_CLEAR_NIGHT):
            return ATTR_CONDITION_SUNNY if is_up(self.hass) else ATTR_CONDITION_CLEAR_NIGHT
        return condition

    def _forecast_condition_now(self) -> str | None:
        city = self._city
        if city is None or not city.days:
            return None
        now = dt_util.now(TZ)
        idx = _current_period_index(now)
        return _period_condition(city.days[0], idx, night=idx in (0, 3))

    @property
    def native_temperature(self) -> float | None:
        station = self._station
        return station.temperature if station else None

    @property
    def humidity(self) -> float | None:
        station = self._station
        return station.humidity if station else None

    @property
    def native_wind_speed(self) -> float | None:
        station = self._station
        return station.wind_speed if station else None

    @property
    def wind_bearing(self) -> float | None:
        station = self._station
        return station.wind_bearing if station else None

    @property
    def native_visibility(self) -> float | None:
        station = self._station
        return station.visibility if station else None

    @property
    def uv_index(self) -> float | None:
        return self.coordinator.data.uv.get(self._city_key)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        city = self._city
        station = self._station
        attrs: dict[str, Any] = {
            "region": REGIONS.get(self._region, self._region),
            "localidad": city.name if city else self._city_key,
        }
        if city is not None:
            attrs["pronostico_redactado"] = city.issued
            if city.days:
                today = city.days[0]
                attrs["pronostico_hoy"] = {
                    PERIODS[i]: text
                    for i, text in enumerate(today.texts[: len(PERIODS)])
                    if text
                }
        if self._station_code != NO_STATION:
            attrs["estacion"] = STATIONS.get(self._station_code, self._station_code)
            attrs["estacion_codigo"] = self._station_code
        if station is not None:
            attrs["hora_observacion"] = station.time
            attrs["descripcion_observacion"] = station.description
        if self.coordinator.data.stations_updated:
            attrs["observaciones_actualizadas"] = self.coordinator.data.stations_updated
        return attrs

    # -------------------------------------------------------------- pronóstico

    @callback
    def _async_forecast_daily(self) -> list[Forecast] | None:
        city = self._city
        if city is None:
            return None
        base = _base_date(city)
        forecasts: list[Forecast] = []
        for offset, day in enumerate(city.days):
            if day.temp_max is None and day.temp_min is None:
                continue
            item = Forecast(
                datetime=(base + timedelta(days=offset)).isoformat(),
                condition=_day_condition(day),
                native_temperature=day.temp_max,
            )
            if day.temp_min is not None:
                item["native_templow"] = day.temp_min
            forecasts.append(item)
        return forecasts

    @callback
    def _async_forecast_twice_daily(self) -> list[Forecast] | None:
        city = self._city
        if city is None:
            return None
        base = _base_date(city)
        forecasts: list[Forecast] = []
        for offset, day in enumerate(city.days):
            start = base + timedelta(days=offset)
            if day.temp_max is not None:
                forecasts.append(
                    Forecast(
                        datetime=(start + timedelta(hours=6)).isoformat(),
                        is_daytime=True,
                        condition=_day_condition(day),
                        native_temperature=day.temp_max,
                    )
                )
            # La mínima de la noche es la del día siguiente (madrugada).
            next_min = (
                city.days[offset + 1].temp_min if offset + 1 < len(city.days) else None
            )
            night_condition = _night_condition(day)
            if next_min is not None or night_condition is not None:
                forecasts.append(
                    Forecast(
                        datetime=(start + timedelta(hours=20)).isoformat(),
                        is_daytime=False,
                        condition=night_condition,
                        native_temperature=next_min,
                    )
                )
        return forecasts
