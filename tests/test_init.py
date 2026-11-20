"""Tests de flujo de configuración y entidad weather."""

from homeassistant import config_entries
from homeassistant.components.weather import (
    DOMAIN as WEATHER_DOMAIN,
    SERVICE_GET_FORECASTS,
)
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.meteochile.const import (
    CONF_CITY,
    CONF_CITY_NAME,
    CONF_REGION,
    CONF_STATION,
    DOMAIN,
    URL_CURRENT,
    URL_FORECAST,
    URL_UV,
)


async def test_config_flow(hass, mock_dmc):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    regions = result["data_schema"].schema[CONF_REGION].config["options"]
    assert [r["value"] for r in regions] == ["01a", "05", "05m"]
    assert regions[2]["label"] == "Región Metropolitana de Santiago"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REGION: "05m"}
    )
    assert result["step_id"] == "city"
    cities = result["data_schema"].schema[CONF_CITY].config["options"]
    assert [c["value"] for c in cities] == ["colina", "stgoc"]

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CITY: "colina"}
    )
    assert result["step_id"] == "station"
    # Estación sugerida para Colina: Pudahuel
    for key in result["data_schema"].schema:
        if key == CONF_STATION:
            assert key.default() == "SCEL"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_STATION: "SCEL"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Colina"
    assert result["data"] == {CONF_REGION: "05m", CONF_CITY: "colina", CONF_CITY_NAME: "Colina"}
    assert result["options"] == {CONF_STATION: "SCEL"}
    await hass.async_block_till_done()

    state = hass.states.get("weather.meteochile_colina")
    assert state is not None
    assert float(state.attributes["temperature"]) == 15
    assert state.attributes["humidity"] == 63
    assert state.attributes["uv_index"] == 11

    # Segunda vez la misma localidad → abortar
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_REGION: "05m"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CITY: "colina"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_config_flow_cannot_connect(hass, aioclient_mock):
    aioclient_mock.get(URL_FORECAST, status=500)
    aioclient_mock.get(URL_CURRENT, status=500)
    aioclient_mock.get(URL_UV, status=500)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["errors"] == {"base": "cannot_connect"}


def _entry(station="SCEL"):
    return MockConfigEntry(
        domain=DOMAIN,
        unique_id="colina",
        title="Colina",
        data={CONF_REGION: "05m", CONF_CITY: "colina", CONF_CITY_NAME: "Colina"},
        options={CONF_STATION: station},
    )


async def test_weather_entity_and_forecasts(hass, mock_dmc):
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    state = hass.states.get("weather.meteochile_colina")
    assert state.state == "cloudy"
    assert state.attributes["wind_bearing"] == 150
    assert state.attributes["wind_speed"] == 11.1
    assert state.attributes["estacion_codigo"] == "SCEL"
    assert state.attributes["pronostico_hoy"]["mañana"] == "Nublado variando a nubosidad parcial"
    assert "Dirección Meteorológica" in state.attributes["attribution"]

    resp = await hass.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {"entity_id": "weather.meteochile_colina", "type": "daily"},
        blocking=True,
        return_response=True,
    )
    daily = resp["weather.meteochile_colina"]["forecast"]
    assert len(daily) == 5
    assert daily[0]["temperature"] == 27
    assert "templow" not in daily[0]
    assert daily[1]["temperature"] == 25 and daily[1]["templow"] == 13
    assert daily[1]["condition"] == "cloudy"
    assert daily[2]["condition"] == "partlycloudy"
    assert daily[4]["condition"] == "sunny"
    assert daily[0]["datetime"].startswith("2026-11-20T00:00:00-03:00")

    resp = await hass.services.async_call(
        WEATHER_DOMAIN,
        SERVICE_GET_FORECASTS,
        {"entity_id": "weather.meteochile_colina", "type": "twice_daily"},
        blocking=True,
        return_response=True,
    )
    twice = resp["weather.meteochile_colina"]["forecast"]
    assert twice[0]["is_daytime"] is True and twice[0]["temperature"] == 27
    assert twice[1]["is_daytime"] is False and twice[1]["temperature"] == 13
    assert twice[1]["condition"] == "cloudy"

    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_without_station(hass, mock_dmc):
    entry = _entry(station="none")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get("weather.meteochile_colina")
    assert state.state not in ("unavailable", "unknown")
    assert state.attributes.get("temperature") is None


async def test_options_flow(hass, mock_dmc):
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_STATION: "SCQN"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    state = hass.states.get("weather.meteochile_colina")
    assert float(state.attributes["temperature"]) == 16.1


async def test_card_registered(hass, mock_dmc, hass_client):
    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "http", {})
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    urls = hass.data[DATA_EXTRA_MODULE_URL].urls
    assert any(u.startswith("/meteochile/meteochile-card.js?v=") for u in urls)

    client = await hass_client()
    resp = await client.get("/meteochile/meteochile-card.js")
    assert resp.status == 200
    body = await resp.text()
    assert "registry.define(\"meteochile-card\", MeteoChileCard)" in body
