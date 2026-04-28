"""Config flow for the iDM Heatpump Web integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from .idmHeatpumpWeb import idmHeatpumpWeb
from .idmHeatpumpWebNav10 import idmHpWebNav10
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PIN, CONF_TIMEOUT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_entry_flow, config_validation as cv
from functools import partial

from .const import DEF_TIME_BETWEEN_UPDATES, DOMAIN
from .const import DEF_IDM_PIN
from .const import (
    CONF_DISPLAY_NAME,
    CONF_CYCLE_TIME,
    DEF_MIN_TIME_BETWEEN_UPDATES,
    CONF_STAT_DIV,
    CONF_CLK_SET,
    CONF_CLK_HOUR,
    CONF_CLK_HOUR_DEFAULT,
    CONF_NAV10,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DISPLAY_NAME, default="iDM_Web"): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_PIN, default=DEF_IDM_PIN): cv.string,
        vol.Required(CONF_TIMEOUT, default=3): int,
        vol.Required(
            CONF_CYCLE_TIME, default=DEF_TIME_BETWEEN_UPDATES.total_seconds()
        ): int,
        vol.Optional(CONF_STAT_DIV, default=0): int,
        vol.Optional(CONF_CLK_SET, default=0): int,
        vol.Optional(CONF_CLK_HOUR, default=CONF_CLK_HOUR_DEFAULT): int,
        vol.Optional(CONF_NAV10, default=False): bool,
    }
)


class idmWebConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for iDM Heatpump Web."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})

            if user_input[CONF_DISPLAY_NAME].find(" ") != -1:
                errors[CONF_DISPLAY_NAME] = "display_name_no_spaces"
            elif user_input[CONF_TIMEOUT] < 1:
                errors[CONF_TIMEOUT] = "timeout_too_small"
            elif (
                user_input[CONF_CYCLE_TIME]
                < DEF_MIN_TIME_BETWEEN_UPDATES.total_seconds()
            ):
                errors[CONF_CYCLE_TIME] = "cycle_time_too_low"
            elif (user_input[CONF_STAT_DIV] < 3) and (user_input[CONF_STAT_DIV] != 0):
                errors[CONF_STAT_DIV] = "stat_div_too_small"
            elif (user_input[CONF_CLK_SET] < 3) and (user_input[CONF_CLK_SET] != 0):
                errors[CONF_CLK_SET] = "clock_set_deviation_too_small"
            elif (user_input[CONF_CLK_HOUR] < 0) or (user_input[CONF_CLK_HOUR] > 23):
                errors[CONF_CLK_HOUR] = "clock_set_hour_wrong"
            else:
                self._async_abort_entries_match(
                    {CONF_DISPLAY_NAME: user_input[CONF_DISPLAY_NAME]}
                )
                # we want both be unique, the host name and the display name!

                idm = None
                if user_input[CONF_NAV10]:
                    _LOGGER.debug("ConfigFlow: Attempting login with Navigator 10 Web")
                    idm = idmHpWebNav10(
                        user_input[CONF_HOST],
                        user_input[CONF_PIN],
                        user_input[CONF_TIMEOUT],
                    )
                else:
                    _LOGGER.debug("ConfigFlow: Attempting login with Navigator 2.0 Web")
                    idm = idmHeatpumpWeb(
                        self.hass,
                        user_input[CONF_HOST],
                        user_input[CONF_PIN],
                        user_input[CONF_TIMEOUT],
                    )
                result = await idm.async_idm_async_login()
                _LOGGER.debug("ConfigFlow: Login result: %s", result)

                if (result == "unknown_response"):   # this is the sign to switch between Nav2.0 and Nav10
                    user_input[CONF_NAV10] = not user_input[CONF_NAV10]  # switch the nav version and try again
                    _LOGGER.debug("ConfigFlow: Login result was unknown_response, switching nav version and trying again...")

                    idm = None
                    if user_input[CONF_NAV10]:
                        _LOGGER.debug("ConfigFlow: 2nd try: Attempting login with Navigator 10 Web")
                        idm = idmHpWebNav10(
                            user_input[CONF_HOST],
                            user_input[CONF_PIN],
                            user_input[CONF_TIMEOUT],
                        )
                    else:
                        _LOGGER.debug("ConfigFlow: 2nd try: Attempting login with Navigator 2.0 Web")
                        idm = idmHeatpumpWeb(
                            self.hass,
                            user_input[CONF_HOST],
                            user_input[CONF_PIN],
                            user_input[CONF_TIMEOUT],
                        )
                    result = await idm.async_idm_async_login()
                    _LOGGER.debug("ConfigFlow: 2nd login result: %s", result)
                    if (result != "success") and (result != "invalid_pin"):
                        user_input[CONF_NAV10] = not user_input[CONF_NAV10]  # switch back nav version

                if result != "success":
                    if result == "invalid_pin":
                        errors[CONF_PIN] = result
                    errors["base"] = result
                else:
                    devUniqueId = str(user_input[CONF_DISPLAY_NAME]) + "WP"
                    # await self.async_set_unique_id(devUniqueId)
                    # self._abort_if_unique_id_configured()  # this should not happen, since we checked the name, however safe is safe ;-)

                    return self.async_create_entry(
                        title=devUniqueId,
                        data=user_input,
                    )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfigure step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})

            if user_input[CONF_DISPLAY_NAME].find(" ") != -1:
                errors[CONF_DISPLAY_NAME] = "display_name_no_spaces"
            elif user_input[CONF_TIMEOUT] < 1:
                errors[CONF_TIMEOUT] = "timeout_too_small"
            elif (
                user_input[CONF_CYCLE_TIME]
                < DEF_MIN_TIME_BETWEEN_UPDATES.total_seconds()
            ):
                errors[CONF_CYCLE_TIME] = "cycle_time_too_low"
            elif (user_input[CONF_STAT_DIV] < 3) and (user_input[CONF_STAT_DIV] != 0):
                errors[CONF_STAT_DIV] = "stat_div_too_small"
            elif (user_input[CONF_CLK_SET] < 3) and (user_input[CONF_CLK_SET] != 0):
                errors[CONF_CLK_SET] = "clock_set_deviation_too_small"
            elif (user_input[CONF_CLK_HOUR] < 0) or (user_input[CONF_CLK_HOUR] > 23):
                errors[CONF_CLK_HOUR] = "clock_set_hour_wrong"
            else:
                self._async_abort_entries_match(
                    {CONF_DISPLAY_NAME: user_input[CONF_DISPLAY_NAME]}
                )
                # we want both be unique, the host name and the display name!

                idm = None
                if user_input[CONF_NAV10]:
                    idm = idmHpWebNav10(
                        user_input[CONF_HOST],
                        user_input[CONF_PIN],
                        user_input[CONF_TIMEOUT],
                    )
                else:
                    idm = idmHeatpumpWeb(
                        self.hass,
                        user_input[CONF_HOST],
                        user_input[CONF_PIN],
                        user_input[CONF_TIMEOUT],
                    )
                result = await idm.async_idm_async_login()
                _LOGGER.debug("ConfigFlow: Login result: %s", result)

                if (result == "unknown_response"):   # this is the sign to switch between Nav2.0 and Nav10
                    user_input[CONF_NAV10] = not user_input[CONF_NAV10]  # switch the nav version and try again

                    idm = None
                    if user_input[CONF_NAV10]:
                        idm = idmHpWebNav10(
                            user_input[CONF_HOST],
                            user_input[CONF_PIN],
                            user_input[CONF_TIMEOUT],
                        )
                    else:
                        idm = idmHeatpumpWeb(
                            self.hass,
                            user_input[CONF_HOST],
                            user_input[CONF_PIN],
                            user_input[CONF_TIMEOUT],
                        )
                    result = await idm.async_idm_async_login()
                    _LOGGER.debug("ConfigFlow: 2nd login result: %s", result)
                    if (result != "success") and (result != "invalid_pin"):
                        user_input[CONF_NAV10] = not user_input[CONF_NAV10]  # switch back nav version

                if result != "success":
                    if result == "invalid_pin":
                        errors[CONF_PIN] = result
                    errors["base"] = result
                else:
                    # devUniqueId = str(user_input[CONF_DISPLAY_NAME]) + "web"
                    # await self.async_set_unique_id(devUniqueId)

                    return self.async_update_reload_and_abort(
                        self._get_reconfigure_entry(),
                        data_updates=user_input,
                    )

        displayname_configured = self._get_reconfigure_entry().data.get(
            CONF_DISPLAY_NAME, "iDM_Web"
        )
        host_configured = self._get_reconfigure_entry().data.get(CONF_HOST, "")
        pin_configured = self._get_reconfigure_entry().data.get(CONF_PIN, DEF_IDM_PIN)
        timeout_configured = self._get_reconfigure_entry().data.get(CONF_TIMEOUT, 3)
        cycle_time_configured = self._get_reconfigure_entry().data.get(
            CONF_CYCLE_TIME, DEF_TIME_BETWEEN_UPDATES.total_seconds()
        )
        stat_div_configured = self._get_reconfigure_entry().data.get(CONF_STAT_DIV, 0)
        clk_set_configured = self._get_reconfigure_entry().data.get(CONF_CLK_SET, 0)
        clk_hour_configured = self._get_reconfigure_entry().data.get(CONF_CLK_HOUR, CONF_CLK_HOUR_DEFAULT)
        nav10_configured = self._get_reconfigure_entry().data.get(CONF_NAV10, False)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DISPLAY_NAME, default=displayname_configured
                    ): cv.string,
                    vol.Required(CONF_HOST, default=host_configured): cv.string,
                    vol.Required(CONF_PIN, default=pin_configured): cv.string,
                    vol.Required(CONF_TIMEOUT, default=timeout_configured): int,
                    vol.Required(CONF_CYCLE_TIME, default=cycle_time_configured): int,
                    vol.Optional(CONF_STAT_DIV, default=stat_div_configured): int,
                    vol.Optional(CONF_CLK_SET, default=clk_set_configured): int,
                    vol.Optional(CONF_CLK_HOUR, default=clk_hour_configured): int,
                    vol.Optional(CONF_NAV10, default=nav10_configured): bool,
                }
            ),
            errors=errors,
        )
