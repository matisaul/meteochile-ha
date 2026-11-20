"""Integración MeteoChile (Dirección Meteorológica de Chile) para Home Assistant."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import MeteoChileConfigEntry, MeteoChileCoordinator

PLATFORMS: list[Platform] = [Platform.WEATHER]


async def async_setup_entry(hass: HomeAssistant, entry: MeteoChileConfigEntry) -> bool:
    """Configura una localidad."""
    coordinator = MeteoChileCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MeteoChileConfigEntry) -> bool:
    """Descarga una localidad."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: MeteoChileConfigEntry) -> None:
    """Recarga al cambiar las opciones (ej. estación)."""
    await hass.config_entries.async_reload(entry.entry_id)
