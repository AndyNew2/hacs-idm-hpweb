from .idmHeatpumpWeb import idmHeatpumpWeb
from homeassistant.core import HomeAssistant
from .const import CONF_CLK_HOUR_DEFAULT
import logging
import requests

_LOGGER = logging.getLogger(__name__)

# Constants
idm_HeatpumpOperationModes = {
    "off": -1,
    "standby": 0,
    "automatic": 1,
    "away":2,
    "hot_water_only": 4,
    "heating_cooling_only": 5,
}
idm_HeatpumpLegionellaModes = {
    "off": "0",
    "second_heat": "1",
}

idm_HP_SET_OPERATION_MODE_1 = '{"mode_sys":'
idm_HP_SET_OPERATION_MODE_2 = ',"mode_solar":0,"holidays_left":0,"holiday_freshwater":0}'
idm_HP_SET_HOT_WATER_MIN_TEMP = '{"def":46,"edesc":"_HOTWATER_MIN_TEMP","id":"HPFW027","increment":"1","index":2,"max":50,"min":30,"name":"Warmwasserladung Einschalttemperatur","param":"FW027","ptype":0,"type":"int","unit":" °C","value":'
idm_HP_SET_HOT_WATER_MAX_TEMP = '{"def":50,"edesc":"_HOTWATER_MAX_TEMP","id":"HPFW028","increment":"1","index":1,"max":55,"min":35,"name":"Warmwasserladung Ausschalttemperatur","param":"FW028","ptype":0,"type":"int","unit":" °C","value":'
idm_HP_SET_HOT_WATER_BOOST_TEMP = '{"def":60,"edesc":"_BOOST_HOTWATER_TEMPERATURE","id":"HPFW048","increment":"1","index":9,"max":75,"min":55,"name":"Boost-Temperatur","param":"FW048","ptype":0,"type":"int","unit":" °C","value":'
idm_HP_SET_HOT_WATER_LEGIONELLA_FCT_1 = '{"edesc":"_LEGIONELLA_FUNCTION","id":"HPFW044","index":11,"mask":49152,"name":"Legionellenfunktion","param":"FW044","ptype":9,"type":"chooselist","types":{"0":"Aus","1":"Zweiter Wärmeerzeuger"},"value":"'
idm_HP_SET_HOT_WATER_LEGIONELLA_FCT_2 = '","vis":1}'
idm_HP_SET_HOT_WATER_LEGIONELLA_TEMP = '{"def":67,"edesc":"_LEGIONELLA_FUNCTION_TEMPERATURE","id":"HPFW045","increment":"1","index":12,"max":67,"min":60,"name":"Legionellenfunktion - Temperatur","param":"FW045","ptype":0,"type":"int","unit":" °C","value":'
idm_HP_SET_HOT_WATER_LEGIONELLA_DAYS = '{"def":7,"edesc":"_LEGIONELLA_FUNCTION_TIMEINTERVALL","id":"HPFW046","increment":"1","index":13,"max":7,"min":0,"name":"Legionellenfunktion - Zeitintervall","param":"FW046","ptype":0,"type":"int","unit":" Tag(e)","value":'

idM_HP_Std_SET_PARAM_ENDING = ',"vis":1,"fractionSize":0}'


class idmHeatpumpWebService(idmHeatpumpWeb):
    """idmHeatpumpWeb Service Class."""

    def __init__(self, hass: HomeAssistant, host: str, pin: str, timeout: int, statDiv: int = 0,
        clkSet: int = 0, clk_set_hour: int = CONF_CLK_HOUR_DEFAULT ) -> None:
        """Initialize idmHeatpumpWeb Service Class."""
        super().__init__(hass, host, pin, timeout, statDiv, clkSet, clk_set_hour)

    async def async_set_heatpump_operation_mode(self, mode: str) -> bool:
        return await self.hass.async_add_executor_job(self.set_heatpump_operation_mode, mode)
    def set_heatpump_operation_mode(self, mode: str) -> bool:
        try:
            result = False
            if mode not in idm_HeatpumpOperationModes:
                _LOGGER.error("Error in set_heatpump_operation_mode: Invalid mode '%s'. Valid modes are: %s", mode, list(idm_HeatpumpOperationModes.keys()))
                return False
            modeNum = idm_HeatpumpOperationModes[mode]
            postIDMHeader = { "Content-Type": "application/json;charset=utf-8", "CSRF-Token": self.csrf_token }
            setModeData = idm_HP_SET_OPERATION_MODE_1 + str(modeNum) + idm_HP_SET_OPERATION_MODE_2
            htPut = self.session.post(self.idmInfoUrl, setModeData, headers=postIDMHeader, timeout=self._timeout)
            if htPut.status_code != 200:
                _LOGGER.warning(".. SetHeatpumpOperationMode received unexpected response code, did not work! Code: "+str(htPut.status_code))
            else:
                afterPos = htPut.text.find('"mode_sys":'+str(modeNum))
                if afterPos == -1:
                    _LOGGER.warning(".. SetHeatpumpOperationMode received unexpected answer, may not work: Answer: "+htPut.text)
                else:
                    result = True
                    _LOGGER.info("Setting HeatpumpOperationMode to '%s' and nb: %d was successful.", mode, modeNum)
            return result
        except Exception as ex:
            _LOGGER.error("Error in set_heatpump_operation_mode: %s", ex)
            return False

    async def async_set_hot_water_min_temp(self, temperature: int) -> bool:
        return await self.hass.async_add_executor_job(self.set_hot_water_min_temp, temperature)
    def set_hot_water_min_temp(self, temperature: int) -> bool:
        try:
            result = False
            if temperature < 30 or temperature > 50:
                _LOGGER.error("Error in set_hot_water_min_temp: Temperature must be between 30 and 50 °C.")
                return False
            postIDMHeader = { "Content-Type": "application/json;charset=utf-8", "CSRF-Token": self.csrf_token }
            setMinTempData = idm_HP_SET_HOT_WATER_MIN_TEMP + str(temperature) + idM_HP_Std_SET_PARAM_ENDING
            htPut = self.session.put(self.idmDataUrl, setMinTempData, headers=postIDMHeader, timeout=self._timeout)
            if htPut.status_code != 200:
                _LOGGER.warning(".. SetHotWaterMinTemp received unexpected response code, did not work! Code: "+str(htPut.status_code))
            else:
                afterPos = htPut.text.find('"status": "OK"')
                if afterPos == -1:
                    _LOGGER.warning(".. SetHotWaterMinTemp received unexpected answer, may not work: Answer: "+htPut.text)
                else:
                    result = True
                    _LOGGER.info("Setting HotWaterMinTemp to %d °C was successful.", temperature)
            return result
        except Exception as ex:
            _LOGGER.error("Error in set_hot_water_min_temp: %s", ex)
            return False

    async def async_set_hot_water_max_temp(self, temperature: int) -> bool:
        return await self.hass.async_add_executor_job(self.set_hot_water_max_temp, temperature)
    def set_hot_water_max_temp(self, temperature: int) -> bool:
        try:
            result = False
            if temperature < 35 or temperature > 55:
                _LOGGER.error("Error in set_hot_water_max_temp: Temperature must be between 35 and 55 °C.")
                return False
            postIDMHeader = { "Content-Type": "application/json;charset=utf-8", "CSRF-Token": self.csrf_token }
            setMaxTempData = idm_HP_SET_HOT_WATER_MAX_TEMP + str(temperature) + idM_HP_Std_SET_PARAM_ENDING
            htPut = self.session.put(self.idmDataUrl, setMaxTempData, headers=postIDMHeader, timeout=self._timeout)
            if htPut.status_code != 200:
                _LOGGER.warning(".. SetHotWaterMaxTemp received unexpected response code, did not work! Code: "+str(htPut.status_code))
            else:
                afterPos = htPut.text.find('"status": "OK"')
                if afterPos == -1:
                    _LOGGER.warning(".. SetHotWaterMaxTemp received unexpected answer, may not work: Answer: "+htPut.text)
                else:
                    result = True
                    _LOGGER.info("Setting HotWaterMaxTemp to %d °C was successful.", temperature)
            return result
        except Exception as ex:
            _LOGGER.error("Error in set_hot_water_max_temp: %s", ex)
            return False

    async def async_set_hot_water_boost_temp(self, temperature: int) -> bool:
        """Set Hot Water Boost Temperature async."""
        return await self.hass.async_add_executor_job(self.set_hot_water_boost_temp, temperature)
    def set_hot_water_boost_temp(self, temperature: int) -> bool:
        """Set Hot Water Boost Temperature."""
        try:
            result = False
            if temperature < 55 or temperature > 75:
                _LOGGER.error("Error in set_hot_water_boost_temp: Temperature must be between 55 and 75 °C.")
                return False
            postIDMHeader = { "Content-Type": "application/json;charset=utf-8", "CSRF-Token": self.csrf_token }
            setBoostTempData = idm_HP_SET_HOT_WATER_BOOST_TEMP + str(temperature) + idM_HP_Std_SET_PARAM_ENDING
            htPut = self.session.put(self.idmDataUrl, setBoostTempData, headers=postIDMHeader, timeout=self._timeout)
            if htPut.status_code != 200:
                _LOGGER.warning(".. SetHotWaterBoostTemp received unexpected response code, did not work! Code: "+str(htPut.status_code))
            else:
                afterPos = htPut.text.find('"status": "OK"')
                if afterPos == -1:
                    _LOGGER.warning(".. SetHotWaterBoostTemp received unexpected answer, may not work: Answer: "+htPut.text)
                else:
                    result = True
                    _LOGGER.info("Setting HotWaterBoostTemp to %d °C was successful.", temperature)
            return result
        except Exception as ex:
            _LOGGER.error("Error in set_hot_water_boost_temp: %s", ex)
            return False

    async def async_set_hot_water_legionella_fct(self, mode: str) -> bool:
        """Set Hot Water Legionella Function async."""
        return await self.hass.async_add_executor_job(self.set_hot_water_legionella_fct, mode)
    def set_hot_water_legionella_fct(self, mode: str) -> bool:
        """Set Hot Water Legionella Function."""
        try:
            result = False
            if mode not in idm_HeatpumpLegionellaModes:
                _LOGGER.error("Error in set_hot_water_legionella_function: Invalid mode '%s'. Valid modes are: %s", mode, list(idm_HeatpumpLegionellaModes.keys()))
                return False
            modeVal = idm_HeatpumpLegionellaModes[mode]
            postIDMHeader = { "Content-Type": "application/json;charset=utf-8", "CSRF-Token": self.csrf_token }
            setLegionellaModeData = idm_HP_SET_HOT_WATER_LEGIONELLA_FCT_1 + modeVal + idm_HP_SET_HOT_WATER_LEGIONELLA_FCT_2
            htPut = self.session.put(self.idmDataUrl, setLegionellaModeData, headers=postIDMHeader, timeout=self._timeout)
            if htPut.status_code != 200:
                _LOGGER.warning(".. SetHotWaterLegionellaFunction received unexpected response code, did not work! Code: %d", htPut.status_code)
            else:
                result = True
                _LOGGER.info("Setting HotWaterLegionellaFunction to mode '%s': '%s' was successful.", mode, modeVal)
            return result
        except Exception as ex:
            _LOGGER.error("Error in set_hot_water_legionella_function: %s", ex)
            return False

    async def async_set_hot_water_legionella_temp(self, temperature: int) -> bool:
        """Set Hot Water Legionella Temperature async."""
        return await self.hass.async_add_executor_job(self.set_hot_water_legionella_temp, temperature)
    def set_hot_water_legionella_temp(self, temperature: int) -> bool:
        """Set Hot Water Legionella Temperature."""
        try:
            result = False
            if temperature < 60 or temperature > 67:
                _LOGGER.error("Error in set_hot_water_legionella_temp: Temperature must be between 60 and 67 °C.")
                return False
            postIDMHeader = { "Content-Type": "application/json;charset=utf-8", "CSRF-Token": self.csrf_token }
            setLegionellaTempData = idm_HP_SET_HOT_WATER_LEGIONELLA_TEMP + str(temperature) + idM_HP_Std_SET_PARAM_ENDING
            htPut = self.session.put(self.idmDataUrl, setLegionellaTempData, headers=postIDMHeader, timeout=self._timeout)
            if htPut.status_code != 200:
                _LOGGER.warning(".. SetHotWaterLegionellaTemp received unexpected response code, did not work! Code: "+str(htPut.status_code))
            else:
                afterPos = htPut.text.find('"status": "OK"')
                if afterPos == -1:
                    _LOGGER.warning(".. SetHotWaterLegionellaTemp received unexpected answer, may not work: Answer: "+htPut.text)
                else:
                    result = True
                    _LOGGER.info("Setting HotWaterLegionellaTemp to %d °C was successful.", temperature)
            return result
        except Exception as ex:
            _LOGGER.error("Error in set_hot_water_legionella_temp: %s", ex)
            return False

    async def async_set_hot_water_legionella_days(self, days: int) -> bool:
        """Set Hot Water Legionella Days async."""
        return await self.hass.async_add_executor_job(self.set_hot_water_legionella_days, days)
    def set_hot_water_legionella_days(self, days: int) -> bool:
        """Set Hot Water Legionella Days."""
        try:
            result = False
            if days < 0 or days > 7:
                _LOGGER.error("Error in set_hot_water_legionella_days: Days must be between 0 and 7.")
                return False
            postIDMHeader = { "Content-Type": "application/json;charset=utf-8", "CSRF-Token": self.csrf_token }
            setLegionellaDaysData = idm_HP_SET_HOT_WATER_LEGIONELLA_DAYS + str(days) + idM_HP_Std_SET_PARAM_ENDING
            htPut = self.session.put(self.idmDataUrl, setLegionellaDaysData, headers=postIDMHeader, timeout=self._timeout)
            if htPut.status_code != 200:
                _LOGGER.warning(".. SetHotWaterLegionellaDays received unexpected response code, did not work! Code: "+str(htPut.status_code))
            else:
                afterPos = htPut.text.find('"status": "OK"')
                if afterPos == -1:
                    _LOGGER.warning(".. SetHotWaterLegionellaDays received unexpected answer, may not work: Answer: "+htPut.text)
                else:
                    result = True
                    _LOGGER.info("Setting HotWaterLegionellaDays to %d days was successful.", days)
            return result
        except Exception as ex:
            _LOGGER.error("Error in set_hot_water_legionella_days: %s", ex)
            return False
