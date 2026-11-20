"""Fixtures comunes."""

from pathlib import Path

import pytest

from custom_components.meteochile.const import URL_CURRENT, URL_FORECAST, URL_UV

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_dmc(aioclient_mock):
    aioclient_mock.get(URL_FORECAST, content=load("pronostico.js"))
    aioclient_mock.get(URL_CURRENT, content=load("condicionactual.js"))
    aioclient_mock.get(URL_UV, content=load("pronostico_radiacion_uv.js"))
    return aioclient_mock
