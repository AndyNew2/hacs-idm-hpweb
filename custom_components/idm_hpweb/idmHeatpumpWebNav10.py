import asyncio
import websockets

from datetime import datetime, timedelta
from homeassistant.util import dt as dt_util
from .const import CONF_CLK_HOUR_DEFAULT
import logging
_LOGGER = logging.getLogger(__name__)


idmReadAheadBlock = 4092
idmKeyIntro = "<tr><td>"
idmKeyEnding = "</td><td>"
idmDescrIntro = "</td><td>"
idmValueIntro = "</td><td>"
idmValueEnding = "</td><td>"
idmEntryEnding = "</td></tr>"
idmSectionDelimiter = '"edesc":'


iDM_Nav10_InfoRequestStart = '{"controller": "setting", "command": "detail", "data": {"settingId": "'
iDM_Nav10_InfoRequestEnd = '"}}'

iDM_Nav10_SettingIDs = [
    "4768",  # Sensor values
    "4775",  # Digital Inputs
    "4782",  # Analogue Outputs
    "4789",  # Digital Outputs
    "4754",  # System Information
]


iDMExtraData_de = [
    ("<tr><td>Software Version</td>", "<td>", "</td></tr>", "software_version"),
    ("<tr><td>Regler Online</td>", "<td>", "h</td></tr>", "regler_online"),
    ("<tr><td>Laufzeit Stufe&nbsp1</td>", "<td>", "h</td></tr>", "runtime_nb_1"),
    ("<tr><td>Schaltzyklen Stufe&nbsp1</td>", "<td>", "</td></tr>", "switch_cycles_nb_1"),
    ("<tr><td>Laufzeit 2.Wärmeerzeuger</td>", "<td>", "h</td></tr>", "runtime_nb_2"),
    ("<tr><td>Schaltzyklen 2.Wärmeerzeuger</td>", "<td>", "</td></tr>", "switch_cycles_nb_2"),
    ("<tr><td>Laufzeit Heizen</td>", "<td>", "h</td></tr>", "runtime_heating"),
    ("<tr><td>Laufzeit Kühlen</td>", "<td>", "h</td></tr>", "runtime_cooling"),
    ("<tr><td>Laufzeit Warmwasser</td>", "<td>", "h</td></tr>", "runtime_hotwater"),
    ("<tr><td>Laufzeit Abtauen</td>", "<td>", "h</td></tr>", "runtime_defrosting"),
]

idmSensorDefinitions_de = {
    # idm Input Output values
    "B32": "outside_air_temperature",
    "B33": "flow_temperature",
    "B34": "return_temperature",
    "B38": "heatstore_temperature",
    "B45": "loading_temperature",
    "B48": "water_temp_top",
    "B41": "water_temp_bottom",
    "B51": "flow_temp_HK_A",
    "B53": "flow_temp_HK_C",
    "B71": "hotgas_temperature",
    "B37": "airsource_temperature",
    "B79": "verdampfer_austritt_temperature",
    "B78": "verdamper_pressure",
    "B78v": "verdampfungs_temperatur",
    "B86v": "condenser_temperature",
    "B86": "condenser_pressure",
    "B87": "liquid_line_temperature",
    "Platinentemperatur": "board_temperature",
    "B2": "flowmeter",
    "Batteriespannung Zentraleinheit": "battery_voltage_central_unit",
    # idm Digital Inputs
    "Externe Anforderung": "external_request",
    "Ext. Umschaltung H/K": "ext_switch_heating_cooling",
    "EW/EVU Sperrkontakt": "ew_evu_lock_contact",
    "B15": "failure_eheating",
    "B5": "dewpoint_humidity_alarm",
    "ext. Vorrangladung": "ext_hotwater_signal",
    "B10": "high_pressure_error",
    "M73#1": "flow_pump_on",
    # idm Anlogue Outputs
    "M73#2": "flow_pump_percentage",
    "M13#2": "ventilator_voltage",
    "AInOut 80-81": "ainout_80_81",
    "AInOut 82-83": "ainout_82_83",
    "AInOut 84-85": "ainout_84_85",
    "AInOut 86-87": "ainout_86_87",
    "AInOut 88-89": "ainout_88_89",
    "AInOut 180-181": "ainout_180_181",
    # idm Digital Outputs
    "M73#3": "flow_pump_activated",
    "M51": "4way_valve_circuit1",
    "Verdichterheizung": "compressor_heating",
    "E1": "compressor_heating",
    "M31": "pump_heating_circuitA",
    "M33": "pump_heating_circuitC",
    "M41": "mixer_heating_circuitA",
    "M43": "mixer_heating_circuitC",
    "M64": "hotwater_circulation_pump",
    "E31": "siphon_heating",
    "E32.1": "siphon_heating",
    "M13#3": "Drehrichtung Ventilator 1",
    "Elektroheizeinsatz 1kW": "e_heater_1kw_on",
    "Elektroheizeinsatz 2kW": "e_heater_2kw_on",
    "Elektroheizeinsatz 3kW": "e_heater_3kw_on",
    "M61": "valve_heating/cooling",
    "M62": "valve_warm/cold",
    "2. Wärmeerzeuger": "heat_generator_2nd",
    "M63": "value_heating/hotwater",
    # idm Service Parameter
    "Überhitzung 1": "super_heating_1",
    "Unterkühlung": "sub_cooling",
    "Ventilposition": "valve_position",
    "Ventilpos. Unterk.": "valve_pos_sub_cool",
    "Ventilpos. EVDMini": "valve_pos_evdmini",
    # idm PV Parameter (if PV is configured in iDM)
    "mom./prog. Leistung Heizen": "cur_exp_power_heating",
    "mom./prog. Leistung Kühlen": "cur_exp_power_cooling",
    "mom./prog. Leistung Vorrang": "cur_exp_power_hotwater",
    "Wärmepumpe Aufnahmeleistung": "cur_el_power",
}

idmStatDefinitions_de = {
    '"name":"Heizen"': "heating",
    '"name":"Kühlen"': "cooling",
    '"name":"Warmwasser"': "hotwater",
    '"name":"Abtauung"': "defrost",
}


iDMExtraData_en = [
    ("<tr><td>Software Version</td>", "<td>", "</td></tr>", "software_version"),
    ("<tr><td>Controller Online</td>", "<td>", "h</td></tr>", "regler_online"),
    ("<tr><td>Runtime Stage&nbsp1</td>", "<td>", "h</td></tr>", "runtime_nb_1"),
    ("<tr><td>Starts Stage&nbsp1</td>", "<td>", "</td></tr>", "switch_cycles_nb_1"),
    ("<tr><td>Runtime 2nd Stage</td>", "<td>", "h</td></tr>", "runtime_nb_2"),
    ("<tr><td>Starts 2nd Stage</td>", "<td>", "</td></tr>", "switch_cycles_nb_2"),
    ("<tr><td>Runtime Heating</td>", "<td>", "h</td></tr>", "runtime_heating"),
    ("<tr><td>Runtime Cooling</td>", "<td>", "h</td></tr>", "runtime_cooling"),
    ("<tr><td>Runtime Domestic Hot Water</td>", "<td>", "h</td></tr>", "runtime_hotwater"),
    ("<tr><td>Runtime Defrost</td>", "<td>", "h</td></tr>", "runtime_defrosting"),
]

idmSensorDefinitions_en = {
    # idm Input Output values
    "B32": "outside_air_temperature",
    "B33": "flow_temperature",
    "B34": "return_temperature",
    "B38": "heatstore_temperature",
    "B48": "water_temp_top",
    "B41": "water_temp_bottom",
    "B45": "loading_temperature",
    "B51": "flow_temp_HK_A",
    "B53": "flow_temp_HK_C",
    "B71": "hotgas_temperature",
    "B37": "airsource_temperature",
    "B79": "verdampfer_austritt_temperature",
    "B78": "verdamper_pressure",
    "B78v": "verdampfungs_temperatur",
    "B86v": "condenser_temperature",
    "B86": "condenser_pressure",
    "B87": "liquid_line_temperature",
    "board temperature": "board_temperature",
    "B2": "flowmeter",
    "Battery voltage central unit": "battery_voltage_central_unit",
    # idm Digital Inputs
    "external request": "external_request",
    "ext. heat/cool switch": "ext_switch_heating_cooling",
    "EW/EVU blocking": "ew_evu_lock_contact",
    "B15": "failure_eheating",
    "B5": "dewpoint_humidity_alarm",
    "ext. priority request": "ext_hotwater_signal",
    "B10": "high_pressure_error",
    "M73#1": "flow_pump_on",
    # idm Anlogue Outputs
    "M73#2": "flow_pump_percentage",
    "M13": "ventilator_voltage",
    "AInOut 80-81": "ainout_80_81",
    "AInOut 82-83": "ainout_82_83",
    "AInOut 84-85": "ainout_84_85",
    "AInOut 86-87": "ainout_86_87",
    "AInOut 88-89": "ainout_88_89",
    "AInOut 180-181": "ainout_180_181",
    # idm Digital Outputs
    "M73#3": "flow_pump_activated",
    "M51": "4way_valve_circuit1",
    "compressor heating": "compressor_heating",
    "E1": "compressor_heating",
    "M31": "pump_heating_circuitA",
    "M33": "pump_heating_circuitC",
    "M41": "mixer_heating_circuitA",
    "M43": "mixer_heating_circuitC",
    "M64": "hotwater_circulation_pump",
    "E31": "siphon_heating",
    "E32.1": "siphon_heating",
    "M13#3": "ventilator_direction 1",
    "Electric Heater 1kW": "e_heater_1kw_on",
    "Electric Heater 2kW": "e_heater_2kw_on",
    "Electric Heater 3kW": "e_heater_3kw_on",
    "M61": "valve_heating/cooling",
    "M62": "valve_warm/cold",
    "2. heat generator": "heat_generator_2nd",
    "M63": "value_heating/hotwater",
    # idm Service Parameter
    "Superheating 1": "super_heating_1",
    "Subcooling": "sub_cooling",
    "Valve position": "valve_position",
    "Valve pos. subc.": "valve_pos_sub_cool",
    "Valve pos. EVDMini": "valve_pos_evdmini",
    # idm PV Parameter (if PV is configured in iDM)  Interestingly no english translation yet found in iDM GUI, please fix if seen differently
    "mom./prog. Leistung Heizen": "cur_exp_power_heating",
    "mom./prog. Leistung Kühlen": "cur_exp_power_cooling",
    "mom./prog. Leistung Vorrang": "cur_exp_power_hotwater",
    "Wärmepumpe Aufnahmeleistung": "cur_el_power",
}

idmStatDefinitions_en = {
    '"name":"Heating"': "heating",
    '"name":"Cooling"': "cooling",
    '"name":"Domestic Hot Water"': "hotwater",
    '"name":"Defrost"': "defrost",
}


# Helper classes and functions for parsing responses
class IdmResponseData:  # to store parsed response data  # noqa: D101
    _response = []  # list of tuples (key, answer)

    def __init__(self):
        self._response = []

    def addResp(self, key: str, answer: str) -> None:
        self._response.append((key, answer))

    def lenResp(self) -> int:
        return len(self._response)

    def getResp(self, i):
        return self._response[i]


class idmHpWebNav10:
    """Class to interface with the iDM Heatpump Web."""

    def __init__(
        self,
        host: str,
        pin: str,
        timeout: int,
        statDiv: int = 0,
        clkSet: int = 0,
        clk_set_hour: int = CONF_CLK_HOUR_DEFAULT
    ) -> None:
        """Initialize the iDM Heatpump Web interface."""
        self._host = host
        self._pin = pin
        self._timeout = timeout
        self._ws = None
        self.idmUrl = "ws://" + host + ":61220/?auth_code=" + pin
        #self.idmDataUrl = "http://" + host + idmURL_Settings
        #self.idmHeatpumpUrl = "http://" + host + idmURL_Heatpump
        #self.idmInfoUrl = "http://" + host + idmURL_Info
        self.idmExtraDefn = iDMExtraData_de  # try first english version
        self.idmSensorDefn = idmSensorDefinitions_de
        self.idmStatDefn = idmStatDefinitions_de
        # self.idmSettime_HTTP_PUT_Str = iDM_Settime_HTTP_PUT_Str_de
        self.my_counter = 0
        self.statDiv = statDiv
        self.hasQheatSensor = 0  # by default we assume no heat sesnor is available, once a Q heat sensor values is seen it is set to 1
        self.clkSet = clkSet
        self.clkSetHour = clk_set_hour
        self.clkCheckSetToday = False

    def __del__(self):
        """Destructor to close the websocket connection."""
        try:
            if self._ws is not None:
                self._ws.close()
        except Exception as e:
            _LOGGER.error(f"Nav10_destructor: Error occurred while closing websocket: {e}")

    def get_navigatorName(self) -> str:
        """Get the navigator name of the heatpump web interface."""
        return "Navigator 10 Web"

    def get_host(self) -> str:
        """Get the host of the heatpump web interface."""
        return self._host

    async def async_idm_async_login(self) -> str:
        try:
            if self._ws is not None:
                await self._ws.close(); self._ws = None
        except Exception as e:
            _LOGGER.warning(f"Login: Error occurred while closing existing websocket connection during login: {e}")
        try:
            _LOGGER.debug(f"Attempting to connect to iDM Heatpump Web at {self.idmUrl}")
            self._ws = await websockets.connect(self.idmUrl, open_timeout = self._timeout)
            response = await asyncio.wait_for(self._ws.recv(), timeout=self._timeout)
            _LOGGER.debug(f"Login response: {response}")
            if ("authorized" in response) and ("true" in response):
                return "success"
            if ("authorized" in response) and ("false" in response):
                try:
                    await self._ws.close(); self._ws = None
                except Exception as e: pass
                return "invalid_pin"
            else:
                try:
                    await self._ws.close(); self._ws = None
                except Exception as e: pass
                return "login_failed"

        except websockets.exceptions.ConnectionClosedError as e:
            _LOGGER.error(f"Connection closed error during login: {e}")
            try:
                if self._ws:await self._ws.close(); self._ws = None
            except Exception as e: pass
            return "login_failed"
        except ConnectionRefusedError as e:
            _LOGGER.error(f"Connection refused error during login: {e}")
            try:
                if self._ws:await self._ws.close(); self._ws = None
            except Exception as e: pass
            return "unknown_response"   # we return unknown response, since this is the error code the config flow knows to switch between Nav2.0 and Nav10
        except asyncio.TimeoutError as e:
            _LOGGER.error(f"Timeout error during login: {e}")
            try:
                if self._ws:await self._ws.close(); self._ws = None
            except Exception as e: pass
            return "cannot_connect"
        except Exception as e:
            _LOGGER.error(f"Error during login: {e}")
            try:
                if self._ws:await self._ws.close(); self._ws = None
            except Exception as e: pass
            return "cannot_connect"

    async def async_idm_async_get_data(self) -> IdmResponseData:
        """Async get data from the heatpump web interface."""

        answerData = IdmResponseData()  # initialize an emmpty response
        serviceMode = False

        for indexSettings in range(0,len(iDM_Nav10_SettingIDs)-0):
            request = iDM_Nav10_InfoRequestStart + iDM_Nav10_SettingIDs[indexSettings] + iDM_Nav10_InfoRequestEnd  # will result in '{"controller": "setting", "command": "detail", "data": {"settingId": "4768"}}'
            _LOGGER.debug(f"Sending {indexSettings} request for setting ID {iDM_Nav10_SettingIDs[indexSettings]}: {request}")

            try:
                if (self._ws is None) and (True):  # ### for testing only, remove False
                    _LOGGER.info("Websocket connection not established. Attempting to login.")
                    login_result = await self.async_idm_async_login()
                    if login_result != "success":
                        _LOGGER.error(f"Login failed with result: {login_result}. Cannot fetch data.")
                        return answerData  # return empty data, next fetch will try to reconnect again
                await asyncio.wait_for(self._ws.send(request), timeout=self._timeout)
                response = str(await asyncio.wait_for(self._ws.recv(), timeout=self._timeout))
                _LOGGER.debug(f"Data response received: {response}")
            except websockets.exceptions.ConnectionClosedError as e:
                _LOGGER.info(f"Connection closed error while fetching data: {e}")
                await self.async_idm_async_login()   # try to reconnect, next data fetch should work then
                return answerData  # return empty data, next fetch will try to reconnect again
            except asyncio.TimeoutError as e:
                _LOGGER.error(f"Timeout error while fetching data: {e}")
                return answerData  # return empty data, next fetch will hopefully work
            except Exception as e:
                _LOGGER.error(f"Error occurred while fetching data: {e}")
                return answerData  # return empty data, next fetch will try to reconnect again
                # ### for testing only, comment in return in production

            # response = idmTestResponse2[indexSettings]  # ### for testing only, comment out in production
            # _LOGGER.debug(f"Using test response: {response}")  # ### for testing only, comment out in production

            afterPos=response.find('"settingDetail":')
            if afterPos != -1:
                afterPos += len('"settingDetail":')

                # extract all defined sensor values
                _LOGGER.debug("Parsing data response from IDM Heatpump Web")

                # check id just for logging information
                startPos=response.find('"id":"',afterPos)
                if (startPos != -1):
                    afterPos=response.find('"',startPos+len('"id":"'),startPos+len('"id":"')+10)
                    if (afterPos != -1):
                        idStr=response[startPos+len('"id":"'):afterPos]
                        _LOGGER.debug(f"  ..Parsing settingDetail with id: {idStr}")
                        if (iDM_Nav10_SettingIDs[indexSettings] != idStr):
                            _LOGGER.warning(f"Received settingDetail with unexpected id: {idStr}, expected: {iDM_Nav10_SettingIDs[indexSettings]}")
                    else:
                        _LOGGER.warning("Could not find end of id string in response, parsing might be wrong")
                        afterPos = startPos  # reset afterPos to startPos to avoid parsing errors, we might be able to continue parsing the rest of the response correctly
                else:
                    _LOGGER.warning("Could not find id in response, parsing might be wrong")

                startPos = afterPos
                # check for extra defined values
                if (indexSettings == 4):  # for system information we have to do extra parsing work...
                    for i in self.idmExtraDefn:
                        (key, startDel, endDel, sensorKey) = i
                        # _LOGGER.debug("Extracting extra key: startPos=%d key=%s", startPos, key)
                        (valStr, afterPos) = extractParameterRaw(
                            response,
                            startPos,
                            startPos + idmReadAheadBlock,
                            key,
                            startDel,
                            endDel,
                        )
                        if afterPos > startPos:  # something found
                            answerData.addResp(sensorKey, valStr)
                            startPos = afterPos
                            # _LOGGER.debug("Extracting extra key: afterPos=%d key=%s value=%s",afterPos,key,valStr,
                        else:
                            _LOGGER.debug(
                                "Extra Key %s not found in response for sensor %s. Will be ignored.", key, sensorKey)
                    break  # stop this round no further values are to extract

                keyStr = ""
                while True:
                    (valStr, keyStr, afterPos) = extractParameterInputOutputInSectionWithKey(response, startPos)
                    # _LOGGER.debug(f"Extracted value: {valStr}, key: {keyStr}, next position: {afterPos}")
                    if startPos == afterPos:
                        break  # no more entries in this section or error, do not matter, we stop here
                    # search of key in sensor definitions
                    v = self.idmSensorDefn.get(keyStr)
                    if v is None:
                        # try again with #1, #2, #3 ... in case of multiple same keys in different sections
                        keyStr = keyStr + "#" + str(indexSettings)  # to differenciate multiple same keys in different sections
                        v = self.idmSensorDefn.get(keyStr)
                    if v is None:
                        _LOGGER.debug("Key %s not found in sensor definitions. Will be ignored.", keyStr)
                    else:
                        # extra interpretation of digital input values
                        if v in (
                            "flow_pump_on",
                            "external_request",
                            "ext_switch_heating_cooling",
                            "ext_hotwater_signal",
                            "hotwater_circulation_pump",
                            "siphon_heating",
                            "compressor_heating",
                            "pump_heating_circuitA",
                            "pump_heating_circuitC",
                            "4way_valve_circuit1",
                            "e_heater_1kw_on",
                            "e_heater_2kw_on",
                            "e_heater_3kw_on",
                            "heat_generator_2nd",
                        ):
                            if valStr == "1":
                                valStr = "on"
                            elif valStr == "0":
                                valStr = "off"
                        elif v in (
                            "failure_eheating",
                            "dewpoint_humidity_alarm",
                            "high_pressure_error",
                        ):
                            if valStr == "1":
                                valStr = "OK"
                            elif valStr == "0":
                                valStr = "Problem!"
                        elif v in ("ew_evu_lock_contact"):
                            if valStr == "1":
                                valStr = "off"
                            elif valStr == "0":
                                valStr = "on"
                        elif v == "ainout_80_81":
                            serviceMode = True  # detected Service mode, add further section
                            _LOGGER.debug("Service mode detected, enabling service mode parameters.")
                        if len(keyStr) <= 5:
                            v = keyStr  # for short keys, just use the key as sensor name

                        answerData.addResp(v, valStr)
                    startPos = afterPos
            else:
                _LOGGER.info("Could not find 'settingDetail' in response")

            # _LOGGER.info("Loop count %d", self.my_counter)
            if (indexSettings == 3) and (self.my_counter%5 != 0):
                break # system information is quite static, so reduce polling frequency to relax heatpump interface
            await asyncio.sleep(0.3)  # short sleep to avoid overloading the heatpump web interface with requests

        self.my_counter += 1  # count this loop (for statistics division)
        return answerData





# txt = text to search value for
# startpos = index where search starts
# endpos = index where search ends string len if no limit want to be applied
# searchStrKey = complete string to search for the key for the value
# valueIntro = key for value intro
# valueEnding = key for value ending
# return (string, afterPos) a tuple of the valueString and the position in text after that value string
def extractParameterRaw(txt, startPos, endPos, searchStrKey, valueIntro, valueEnding):
    startP = txt.find(searchStrKey, startPos, endPos)
    if startP == -1:
        return ("SearchStrKey <" + searchStrKey + "> not found", startPos)
    newPos = startP + len(searchStrKey)
    startPosVal = txt.find(valueIntro, newPos, endPos)
    if startPosVal == -1:
        return ("Value intro not found", startPos)
    newPos = startPosVal + len(valueIntro)
    endPosVal = txt.find(valueEnding, newPos, endPos)
    if endPosVal == -1:
        return ("Value ending not found", startPos)

    return (txt[newPos:endPosVal], endPosVal + len(valueEnding))


# txt = text to search value for,
# startpos = index where to start (to overjump begin of string for performance and avoid ambiguity)
# pattern = pattern or idmKey description e.g. "B32"
# return (string, afterPos) a tuple of the valueString and the position in text after that value string
def extractParameterStr(txt, startPos, pattern, descr=""):
    searchStr = idmKeyIntro + pattern + idmKeyEnding
    if descr != "":
        searchStr = idmDescrIntro + descr
    return extractParameterRaw(
        txt,
        startPos,
        startPos + idmReadAheadBlock,
        searchStr,
        idmValueIntro,
        idmValueEnding,
    )



# txt = text to search value for expecting input/output format of idM heatpump web
# startpos = index where to start (to overjump begin of string for performance and avoid ambiguity)
# return (string, key, afterPos) a tripple of the valueString, the key and the position in text after that value string
# afterPos == startPos in case no more values found in that section
def extractParameterInputOutputInSectionWithKey(txt, startPos):
    entryStart = txt.find(idmKeyIntro, startPos, startPos + idmReadAheadBlock)
    if entryStart == -1:
        return ("No more values found", "no key", startPos)
    newPos = txt.find(idmSectionDelimiter, startPos, entryStart)  # in case there is a section delimiter before entry start, we have reached end of section
    if newPos != -1:
        return ("No more entries in this section", "no key", startPos)
    entryEnd = txt.find(idmEntryEnding, entryStart, startPos + idmReadAheadBlock)
    if entryEnd == -1:
        return ("No entry ending found", "no key", startPos)
    # the whole entry is between entryStart and entryEnd
    newPos = entryStart + len(idmKeyIntro)  # position for key is straight after entry begin
    endPos = txt.find(idmKeyEnding, newPos, entryEnd)
    if endPos == -1:
        return ("No key ending found", "no key", startPos)
    keyStr = txt[newPos:endPos]
    if (keyStr == "") or (keyStr == " "):
        # use description as key
        newPos = txt.find(idmDescrIntro, endPos, entryEnd)
        if newPos == -1:
            return ("No description intro found", "no key", startPos)
        newPos += len(idmDescrIntro)
        endPos = txt.find(idmKeyEnding, newPos, entryEnd)
        if endPos == -1:
            return ("No description ending found", "no key", startPos)
        keyStr = txt[newPos:endPos]
        # _LOGGER.debug("Description found: %s", keyStr)
        newPos = endPos + len(idmKeyEnding)  # description ending is the same as value intro, therefore set newPos to it
    else:
        endPos += len(idmKeyEnding)  # we need to search for value intro, but make sure we are after key ending
        newPos = txt.find(idmValueIntro, endPos, entryEnd)
        if newPos == -1:
            return ("No value intro found", keyStr, startPos)
        newPos += len(idmValueIntro)
    endPos = txt.find(idmValueEnding, newPos, entryEnd)
    if endPos == -1:
        return ("No value ending found", keyStr, startPos)
    # _LOGGER.debug("entryFound Key: %s, value = %s", keyStr, txt[newPos:endPos])
    return (txt[newPos:endPos], keyStr, entryEnd + len(idmEntryEnding))
