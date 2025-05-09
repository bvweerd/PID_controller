"""Advanced PID Controller integration."""

from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, CONF_NAME, CONF_SENSOR_ENTITY_ID

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER, Platform.SWITCH]


class PIDDeviceHandle:
    """Shared device handle for a PID controller config entry."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.name = entry.data.get(CONF_NAME)
        self.sensor_entity_id = entry.options.get(CONF_SENSOR_ENTITY_ID, entry.data.get(CONF_SENSOR_ENTITY_ID))
        self.last_contributions = (None, None, None)  # (P, I, D)

    def get_number(self, key: str) -> float | None:
        """Get value from number entity by key, using the registry lookup."""
        entity_id = self._get_entity_id("number", key)
        if not entity_id:
            return None
        state = self.hass.states.get(entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                return float(state.state)
            except ValueError:
                pass
        return None

    def get_switch(self, key: str) -> bool:
        """Get boolean from switch entity by key, using the registry lookup."""
        entity_id = self._get_entity_id("switch", key)
        if not entity_id:
            return True  # default on
        state = self.hass.states.get(entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            return state.state == "on"
        return True
        
    def get_input_sensor_value(self) -> float | None:
        """Return the input value from configured sensor."""
        state = self.hass.states.get(self.sensor_entity_id)
        if state and state.state not in ("unknown", "unavailable"):
            try:
                return float(state.state)
            except ValueError:
                _LOGGER.warning(f"Sensor {self.sensor_entity_id} heeft geen geldige waarde. PID-berekening wordt overgeslagen.")
        return None

    def _get_entity_id(self, platform: str, key: str) -> str | None:
        """Return the actual entity_id for this entry and parameter key."""
        reg = er.async_get(self.hass)

        desired = f"{self.entry.entry_id}_{key}"
        return reg.async_get_entity_id(platform, DOMAIN, desired)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Advanced PID Controller from a config entry."""

    sensor_entity_id = entry.options.get(CONF_SENSOR_ENTITY_ID, entry.data.get(CONF_SENSOR_ENTITY_ID))
    state = hass.states.get(sensor_entity_id)
    if state is None or state.state in ("unknown", "unavailable"):
        _LOGGER.warning("Sensor %s not ready; delaying setup", sensor_entity_id)
        raise ConfigEntryNotReady(f"Sensor {sensor_entity_id} not ready")

    handle = PIDDeviceHandle(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = handle

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload PID Controller entry."""
    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        hass.data[DOMAIN].pop(entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
