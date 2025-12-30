"""The iDM Heatpump Web integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PIN, CONF_TIMEOUT
from .const import CONF_DISPLAY_NAME, CONF_CYCLE_TIME, CONF_STAT_DIV

_PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up iDM Heatpump Web from a config entry."""

    displayname = entry.data.get(CONF_DISPLAY_NAME)
    hostname = entry.data.get(CONF_HOST)
    pin = entry.data.get(CONF_PIN)
    timeout = entry.data.get(CONF_TIMEOUT)
    cycle_time = entry.data.get(CONF_CYCLE_TIME)
    stat_div = 0  # default to disabled
    try:
        stat_div = entry.data.get(CONF_STAT_DIV)
    except:
        # we ignore errors here, we work with the default...
        stat_div = 0

    entry.runtime_data = {
        CONF_DISPLAY_NAME: displayname,
        CONF_HOST: hostname,
        CONF_PIN: pin,
        CONF_TIMEOUT: timeout,
        CONF_CYCLE_TIME: cycle_time,
        CONF_STAT_DIV: stat_div,
    }

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)
