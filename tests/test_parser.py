"""Tests del lector de archivos de la DMC."""

from custom_components.meteochile.conditions import to_condition, worst
from custom_components.meteochile.parser import (
    decode_bytes,
    parse_current,
    parse_forecast,
    parse_uv,
    read_js_literal,
)

from .conftest import load


def test_parse_forecast_colina():
    data = parse_forecast(decode_bytes(load("pronostico.js")))
    assert set(data) == {"arica", "valpo", "colina", "stgoc"}
    colina = data["colina"]
    assert colina.name == "Colina"
    assert colina.region == "05m"
    assert colina.base_date == "2026-11-20"
    assert len(colina.days) == 5
    assert colina.days[0].temp_min is None
    assert colina.days[0].temp_max == 27
    assert (colina.days[1].temp_min, colina.days[1].temp_max) == (13, 25)
    assert colina.days[4].temp_max == 31
    assert colina.days[1].label == "sábado 21"
    assert colina.days[0].texts[1] == "Nublado variando a nubosidad parcial"
    assert colina.issued_text.startswith("Información redactada")


def test_parse_forecast_entities_and_extra_days():
    data = parse_forecast(decode_bytes(load("pronostico.js")))
    valpo = data["valpo"]
    assert valpo.name == "Valparaíso"
    # tope 7, pero solo 5 días con temperatura
    assert len(valpo.days) == 5


def test_parse_current():
    stations, updated = parse_current(decode_bytes(load("condicionactual.js")))
    assert updated == "2026-11-20 09:42:02 hrs."
    scel = stations["SCEL"]
    assert scel.temperature == 15
    assert scel.humidity == 63
    assert scel.wind_bearing == 150
    assert scel.wind_speed == 11.1
    assert scel.visibility == 10.0
    assert scel.description == "Nublado"
    assert stations["SCVM"].wind_bearing is None  # VRB
    assert stations["SCQN"].temperature == 16.1
    assert stations["SCQN"].visibility is None
    assert stations["SCFM"].visibility == 7.0
    assert stations["SCFM"].present_weather == "-RA"


def test_parse_uv():
    uv = parse_uv(decode_bytes(load("pronostico_radiacion_uv.js")))
    assert uv["colina"] == 11
    assert uv["valpo"] == 9


def test_js_literal_edge_cases():
    value, _ = read_js_literal("{a: 'x\\'y', b: [1, 2.5, -3,], 'c': {d: null, e: true},}")
    assert value == {"a": "x'y", "b": [1, 2.5, -3], "c": {"d": None, "e": True}}


def test_conditions():
    assert to_condition("Despejado", "despejado.png") == "sunny"
    assert to_condition("Despejado", "despejadonoche.png") == "clear-night"
    assert to_condition("Nubosidad parcial", "parcialalta.png") == "partlycloudy"
    assert to_condition("Nublado", "parcial.png") == "cloudy"
    assert to_condition("Nublado variando a nubosidad parcial", "parcial.png") == "cloudy"
    assert to_condition("Cubierto y lluvia", "lluvia.png") == "rainy"
    assert to_condition("Chubascos", "") == "rainy"
    assert to_condition("Precipitaciones con tormentas eléctricas", "") == "lightning-rainy"
    assert to_condition("Despejado con viento entre 25 y 40 km/h", "viento3.png") == "sunny"
    assert to_condition("Despejado con viento entre 40 y 60 km/h", "viento3.png") == "windy"
    assert to_condition("Nublado con viento entre 40 y 60 km/h", "viento3.png") == "windy-variant"
    assert to_condition("", "viento3.png") is None
    assert to_condition("Escasa nubosidad", "pocasnubes.png") == "partlycloudy"
    assert worst(["sunny", "rainy", None, "cloudy"]) == "rainy"
