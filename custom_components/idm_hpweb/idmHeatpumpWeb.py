# idm Web Interface implementation

import time
import requests
import logging

from functools import partial
from homeassistant.core import HomeAssistant
from datetime import datetime
from datetime import timedelta
from homeassistant.util import dt as dt_util
from .const import CONF_CLK_HOUR_DEFAULT

_LOGGER = logging.getLogger(__name__)

# --------------------------------------------------------------------
# Constants
idmURL_Index = "/index.php"
idmURL_Settings = "/data/settings.php"
idmURL_Heatpump = "/data/heatpump.php"
idmURL_Info = "/data/info.php"
idmURL_Stat_Runtime = "/data/statistics.php?type=heatpump"
idmURL_Stat_GenHeat = "/data/statistics.php?type=amountofheat"
idmURL_Stat_ElCons = "/data/statistics.php?type=baenergyhp"

idmReadAheadBlock = 4092
idmKeyIntro = "<tr><td>"
idmKeyEnding = "</td><td>"
idmDescrIntro = "</td><td>"
idmValueIntro = "</td><td>"
idmValueEnding = "</td><td>"

iDM_IdentificationString_de = '"name":"Allgemeine Einstellungen"'
iDM_Settime_HTTP_PUT_Str_de = '{"edesc":"_SETDATETIME","id":"SSETDATETIME","index":3,"name":"Datum/Uhrzeit","type":"setdt","value":"'  # shall end like this 2026-01-05T14:04:00.000Z"}'

iDMExtraData_de = [
    ("<tr><td>Software Version</td>", "<td>", "</td></tr>", "software_version"),
    ("<tr><td>Regler Online</td>", "<td>", "h</td></tr>", "regler_online"),
    ("<tr><td>Laufzeit Stufe&nbsp1</td>", "<td>", "h</td></tr>", "runtime_nb_1"),
    (
        "<tr><td>Schaltzyklen Stufe&nbsp1</td>",
        "<td>",
        "</td></tr>",
        "switch_cycles_nb_1",
    ),
    ("<tr><td>Laufzeit 2.Wärmeerzeuger</td>", "<td>", "h</td></tr>", "runtime_nb_2"),
    (
        "<tr><td>Schaltzyklen 2.Wärmeerzeuger</td>",
        "<td>",
        "</td></tr>",
        "switch_cycles_nb_2",
    ),
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
    "B48": "water_temp_top",
    "B41": "water_temp_bottom",
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
    "M31": "pump_heating_circuitA",
    "M33": "pump_heating_circuitC",
    "M43": "mixer_heating_circuitC",
    "M64": "hotwater_circulation_pump",
    "E31": "siphon_heating",
    "Elektroheizeinsatz 1kW": "e_heater_1kw_on",
    "Elektroheizeinsatz 2kW": "e_heater_2kw_on",
    "Elektroheizeinsatz 3kW": "e_heater_3kw_on",
    "M61": "valve_heating/cooling",
    "M62": "valve_warm/cold",
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

iDM_IdentificationString_en = '"name":"General Settings"'
iDM_Settime_HTTP_PUT_Str_en = '{"edesc":"_SETDATETIME","id":"SSETDATETIME","index":3,"name":"Date/time","type":"setdt","value":"'  # shall end like this 2026-01-05T14:04:00.000Z"}'
iDMExtraData_en = [
    ("<tr><td>Software Version</td>", "<td>", "</td></tr>", "software_version"),
    ("<tr><td>Controller Online</td>", "<td>", "h</td></tr>", "regler_online"),
    ("<tr><td>Runtime Stage&nbsp1</td>", "<td>", "h</td></tr>", "runtime_nb_1"),
    ("<tr><td>Starts Stage&nbsp1</td>", "<td>", "</td></tr>", "switch_cycles_nb_1"),
    ("<tr><td>Runtime 2nd Stage</td>", "<td>", "h</td></tr>", "runtime_nb_2"),
    ("<tr><td>Starts 2nd Stage</td>", "<td>", "</td></tr>", "switch_cycles_nb_2"),
    ("<tr><td>Runtime Heating</td>", "<td>", "h</td></tr>", "runtime_heating"),
    ("<tr><td>Runtime Cooling</td>", "<td>", "h</td></tr>", "runtime_cooling"),
    (
        "<tr><td>Runtime Domestic Hot Water</td>",
        "<td>",
        "h</td></tr>",
        "runtime_hotwater",
    ),
    ("<tr><td>Runtime Defrost</td>", "<td>", "h</td></tr>", "runtime_defrosting"),
]

idmSensorDefinitions_en = {
    # idm Input Output values
    "B32": "outside_air_temperature",
    "B33": "flow_temperature",
    "B34": "return_temperature",
    "B48": "water_temp_top",
    "B41": "water_temp_bottom",
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
    "M31": "pump_heating_circuitA",
    "M33": "pump_heating_circuitC",
    "M43": "mixer_heating_circuitC",
    "M64": "hotwater_circulation_pump",
    "E31": "siphon_heating",
    "Electric Heater 1kW": "e_heater_1kw_on",
    "Electric Heater 2kW": "e_heater_2kw_on",
    "Electric Heater 3kW": "e_heater_3kw_on",
    "M61": "valve_heating/cooling",
    "M62": "valve_warm/cold",
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


class idmHeatpumpWeb:
    """Class to interface with the iDM Heatpump Web."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        pin: str,
        timeout: int,
        statDiv: int,
        clkSet: int = 0,
        clk_set_hour: int = CONF_CLK_HOUR_DEFAULT,
    ) -> None:
        """Initialize the iDM Heatpump Web interface."""
        self.hass = hass
        self._host = host
        self._pin = pin
        self._timeout = timeout
        self.session = requests.Session()
        self.csrf_token = None
        self.idmUrl = "http://" + host + idmURL_Index
        self.idmDataUrl = "http://" + host + idmURL_Settings
        self.idmHeatpumpUrl = "http://" + host + idmURL_Heatpump
        self.idmInfoUrl = "http://" + host + idmURL_Info
        self.idmExtraDefn = iDMExtraData_en  # try first english version
        self.idmSensorDefn = idmSensorDefinitions_en
        self.iDM_IdentificationString = iDM_IdentificationString_en
        self.idmStatDefn = idmStatDefinitions_en
        self.idmSettime_HTTP_PUT_Str = iDM_Settime_HTTP_PUT_Str_en
        self.my_counter = -1
        self.statDiv = statDiv
        self.hasQheatSensor = 0  # by default we assume no heat sesnor is available, once a Q heat sensor values is seen it is set to 1
        self.clkSet = clkSet
        self.clkSetHour = clk_set_hour
        self.clkCheckSetToday = False

    async def async_idm_async_login(self) -> str:
        """Async Login to the heatpump web interface."""
        return await self.hass.async_add_executor_job(blocking_idm_login_function, self)

    async def async_idm_async_get_data(self) -> IdmResponseData:
        """Async get data from the heatpump web interface."""
        return await self.hass.async_add_executor_job(
            blocking_idm_get_data_function, self
        )

    # return str: "success" or "cannot_connect" or "invalid_pin" or "unknown"
    def idm_login(self) -> str:
        """Log in to the heatpump web interface."""
        try:
            payload = {"pin": self._pin}
            response = self.session.post(
                self.idmUrl,
                payload,
                self._timeout,
            )
            response.raise_for_status()
            if response.status_code == 200:
                txt = response.text
                if txt.find("Authorization Required") > 0:
                    return "invalid_pin"

                startpos = txt.find('csrf_token="')
                if startpos == -1:
                    return "unknown"
                endpos = txt.find('"', startpos + 12, startpos + 132)
                if endpos == -1:
                    return "unknown"
                self.csrf_token = txt[startpos + 12 : endpos]
                return "success"

            return "cannot_connect"
        except requests.RequestException:
            return "cannot_connect"

    def get_DataUpdate(self) -> IdmResponseData:
        """Get new data from the heatpump web interface."""
        answerData = IdmResponseData()
        addHeader = {
            "CSRF-Token": self.csrf_token,
        }
        postIDMHeader = {
            "Content-Type": "application/json;charset=utf-8",
            "CSRF-Token": self.csrf_token,
        }

        _LOGGER.debug(
            "Fetching data from IDM Heatpump Web interface: CSRF-Token=%s",
            self.csrf_token,
        )

        try:
            response = self.session.get(
                self.idmDataUrl, headers=addHeader, timeout=self._timeout
            )
            if response.status_code == 200:
                txt = response.text
                startPos = txt.find('"invalid csrf token"', 0, 128)
                if startPos != -1:
                    _LOGGER.warning("CSRF token invalid, redoing login")
                    ## redo login with pin and csrf token extraction
                    time.sleep(1)
                    result = self.idm_login()
                    return answerData

                startPos = txt.find(self.iDM_IdentificationString, 0, len(txt))
                if startPos == -1:
                    _LOGGER.debug("Identification string not found, switch languange.")
                    if (
                        self.iDM_IdentificationString == iDM_IdentificationString_en
                    ):  # was till now English -> try German now
                        self.iDM_IdentificationString = iDM_IdentificationString_de
                        self.idmExtraDefn = iDMExtraData_de
                        self.idmSensorDefn = idmSensorDefinitions_de
                        self.idmStatDefn = idmStatDefinitions_de
                        self.idmSettime_HTTP_PUT_Str = iDM_Settime_HTTP_PUT_Str_de
                    else:  # there needs to be more checks, if further languanges are supported, but for now it is OK that way
                        self.iDM_IdentificationString = iDM_IdentificationString_en
                        self.idmExtraDefn = iDMExtraData_en
                        self.idmSensorDefn = idmSensorDefinitions_en
                        self.idmStatDefn = idmStatDefinitions_en
                        self.idmSettime_HTTP_PUT_Str = iDM_Settime_HTTP_PUT_Str_en

                    # now check the new language
                    startPos = txt.find(self.iDM_IdentificationString, 0, len(txt))
                    if startPos == -1:
                        _LOGGER.warning(
                            "Identification string not found, wrong frame, or unknown language!"
                        )
                        return answerData  # we cannot do anything else with this frame, so discard it and stop processing here

                self.my_counter += 1  # count this loop
                afterPos = 0
                for i in self.idmExtraDefn:
                    (key, startDel, endDel, sensorKey) = i
                    # _LOGGER.debug("Extracting extra key: startPos=%d key=%s", startPos, key)
                    (valStr, afterPos) = extractParameterRaw(
                        txt,
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
                            "Extra Key %s not found in response for sensor",
                            key,
                            sensorKey,
                        )

                afterPos = txt.find('"edesc":"_INPUTS_OUTPUTS_INFO"', startPos)
                if afterPos == -1:
                    _LOGGER.warning(
                        "Wrong answer received, no values can be extracted!"
                    )
                    return answerData

                # extract all defined sensor values
                _LOGGER.debug("Parsing data response from IDM Heatpump Web")
                startPos = afterPos
                serviceMode = False
                for k, v in self.idmSensorDefn.items():
                    sensorKey = k  # by default use k as sensor key
                    if (v == "super_heating_1") or (v == "cur_exp_power_heating"):
                        if serviceMode:
                            # we need to help, since service mode responses are very long
                            afterPos = txt.find(k, startPos)
                            if afterPos != -1:
                                startPos = (
                                    afterPos - 50
                                )  # set startPos shortly before finding, so intro can be found as well
                        else:
                            # check if there are PV data in response
                            startPos = txt.find('"edesc":"_PV"', startPos)
                            if startPos == -1:
                                break  # if not PV data break loop here to avoid endless searching for nothing

                    if len(k) <= 5:
                        searchK = k
                        hashPos = k.find("#")
                        if hashPos != -1:
                            searchK = k[0:hashPos]
                            # unfortunately some keys are used more than once, we solve this with the context (position of the data)
                        (valStr, afterPos) = extractParameterStr(txt, startPos, searchK)
                    else:
                        sensorKey = v  # by long search strings (localized) use the description field as index
                        (valStr, afterPos) = extractParameterStr(txt, startPos, "", k)
                    # _LOGGER.debug("Parsed %s: %s", k, valStr)

                    # extra interpretation of digital input values
                    if v in (
                        "flow_pump_on",
                        "external_request",
                        "ext_switch_heating_cooling",
                        "ext_hotwater_signal",
                        "hotwater_circulation_pump",
                        "siphon_heating",
                        "pump_heating_circuitA",
                        "pump_heating_circuitC",
                        "4way_valve_circuit1",
                        "e_heater_1kw_on",
                        "e_heater_2kw_on",
                        "e_heater_3kw_on",
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
                    elif (v == "ainout_80_81") and (afterPos > startPos):
                        serviceMode = (
                            True  # detected Service mode, longer search needed
                        )

                    if afterPos > startPos:  # something found
                        answerData.addResp(sensorKey, valStr)
                        startPos = afterPos
                    else:
                        _LOGGER.debug("Key %s not found in response", k)

                time.sleep(
                    0.4
                )  # relax a little bit to avoid idm heatpump web overloads
                response = self.session.get(
                    self.idmHeatpumpUrl, headers=addHeader, timeout=self._timeout
                )
                if response.status_code == 200:
                    txt = response.text
                    startPos = txt.find('{"flow":{')
                    while startPos != -1:
                        hc_mode = ""  # default for not found
                        afterPos = txt.find(
                            '"hcmode":', startPos, startPos + idmReadAheadBlock
                        )
                        if afterPos > startPos:
                            if txt[afterPos + 9] == "0":
                                hc_mode = "off"
                            elif txt[afterPos + 9] == "1":
                                hc_mode = "heating"
                            elif txt[afterPos + 9] == "2":
                                hc_mode = "cooling"  # according ModbusTCP documentation, this should be correct
                            else:
                                hc_mode = txt[afterPos + 9]

                        (valStr, afterPos) = extractParameterRaw(
                            txt,
                            startPos,
                            startPos + idmReadAheadBlock,
                            '"temperatures":{',
                            '"set":"',
                            '"',
                        )
                        if afterPos > startPos:
                            startPos = afterPos
                            afterPos = txt.find('"hk":"', startPos)
                            if afterPos != -1:
                                heatCircuitLetter = txt[afterPos + 6]
                                if (heatCircuitLetter >= "A") and (
                                    heatCircuitLetter <= "G"
                                ):
                                    answerData.addResp(
                                        "flow_temp_set_hc_" + heatCircuitLetter,
                                        valStr,
                                    )
                                    if hc_mode != "":
                                        answerData.addResp(
                                            "mode_heatcirc_" + heatCircuitLetter,
                                            hc_mode,
                                        )
                                startPos = afterPos
                            else:
                                afterPos = (
                                    startPos  # restore afterPos for futher values
                                )
                                startPos = -1  # to abort this while loop
                        else:
                            startPos = -1  # this aborts while loop

                    startPos = afterPos  # search new values after heat circuit set temperatures
                    (valStr, afterPos) = extractParameterRaw(
                        txt,
                        startPos,
                        startPos + idmReadAheadBlock,
                        '"pv":{',
                        '"hp":"',
                        '"',
                    )
                    if afterPos > startPos:
                        answerData.addResp(
                            "cur_el_power_pre",
                            valStr,
                        )
                    startPos = afterPos  # search new values after heat circuit set temperatures
                    (valStr, afterPos) = extractParameterRaw(
                        txt,
                        startPos,
                        startPos + idmReadAheadBlock,
                        '"system":{"q":{',
                        '"value":"',
                        '"',
                    )
                    if afterPos > startPos:
                        answerData.addResp(
                            "cur_heat_power",
                            valStr,
                        )
                        self.hasQheatSensor = 1  # we have seen the Q value, so a gen. heat sesnor is available (may not be the case for all iDM heatpumps)
                    elif self.hasQheatSensor == 1:
                        # if we previously have seen a Q sensor, not providing it now means 0 heat generation, however do not create sensor, if no sensor have seen at all
                        answerData.addResp(
                            "cur_heat_power",
                            "0.0",
                        )
                    startPos = afterPos
                    afterPos = txt.find(
                        '"stages":', startPos, startPos + idmReadAheadBlock
                    )
                    valStr = "off"  # there is no value for compressor off, therefore we default it to off
                    if afterPos > startPos:
                        # if stages exist, it means the heatpump compressor or heater runs
                        valStr = txt[afterPos + 9]
                        if valStr == "0":
                            valStr = "on_0"  # not expected, but added to be shown in case it happens...
                        elif valStr == "1":
                            valStr = "on"
                        elif valStr == "2":
                            valStr = "on_2"  # assuming this is seens as the 2nd source
                        # we do not expect other values than 0,1,2 if it occurs we just leave it to the entity...
                        startPos = afterPos
                    answerData.addResp(  # this is special to compressor state, we always write the state, even attribute is not found
                        "heatpump_compressor",
                        valStr,
                    )
                    afterPos = txt.find(
                        '"sysmode":', startPos, startPos + idmReadAheadBlock
                    )
                    if afterPos > startPos:
                        valStr = txt[afterPos + 10]
                        if valStr == "0":
                            valStr = "off"
                        elif valStr == "1":
                            valStr = "heating"
                        elif valStr == "2":
                            valStr = "cooling"
                        elif valStr == "4":
                            valStr = "hotwater"
                        elif valStr == "8":
                            valStr = "defrost"

                        # we do not expect other values than 0 to 8, if it occurs we just leave it to the entity...
                        answerData.addResp(
                            "heatpump_op_mode",
                            valStr,
                        )

                if self.statDiv >= 3:
                    idmUrlStat = None
                    keyValIntro = ""
                    if (self.my_counter % self.statDiv) == 0:
                        # get statistics for runtime
                        idmUrlStat = "http://" + self._host + idmURL_Stat_Runtime
                        keyValIntro = "stat_runtime_"
                    elif (self.my_counter % self.statDiv) == 1:
                        # get statistics for generated heat
                        idmUrlStat = "http://" + self._host + idmURL_Stat_GenHeat
                        keyValIntro = "stat_genheat_"
                    elif (self.my_counter % self.statDiv) == 2:
                        # get statistics for electrical heat consumption
                        idmUrlStat = "http://" + self._host + idmURL_Stat_ElCons
                        keyValIntro = "stat_elcons_"
                    if idmUrlStat:
                        time.sleep(1)  # relax to avoid idm heatpump web overloads
                        response = self.session.get(
                            idmUrlStat, headers=addHeader, timeout=self._timeout
                        )
                        if response.status_code == 200:
                            txt = response.text

                            startPos = txt.find(',"total":')
                            if startPos != -1:
                                index = 0
                                foundStat = [0] * len(self.idmStatDefn)
                                for k, v in self.idmStatDefn.items():
                                    (valStr, afterPos) = extractParameterRaw(
                                        txt,
                                        startPos,
                                        startPos + idmReadAheadBlock,
                                        k,
                                        '"value":',
                                        "}",
                                    )
                                    if afterPos > startPos:  # something found
                                        answerData.addResp(
                                            keyValIntro + "total_" + v, valStr
                                        )
                                        startPos = afterPos
                                        foundStat[index] = 1
                                    else:
                                        _LOGGER.debug("Key %s not found in response", k)
                                    index += 1

                                index = 0
                                (valStr, afterPos) = extractParameterRaw(
                                    txt,
                                    startPos,
                                    startPos + idmReadAheadBlock,
                                    ',"yearly":[',
                                    '"values":[[',
                                    ",",
                                )
                                if afterPos > startPos:
                                    for k, v in self.idmStatDefn.items():
                                        if foundStat[index] == 1:
                                            if (
                                                valStr == ""
                                            ):  # happens for defrost at begin of year, prevent writing unvalid string to entity
                                                valStr = "0.0"
                                            answerData.addResp(
                                                keyValIntro + "cur_year_" + v,
                                                valStr,
                                            )
                                            startPos = afterPos
                                            while (afterPos < len(txt)) and (
                                                (
                                                    (txt[afterPos] >= "0")
                                                    and (txt[afterPos] <= "9")
                                                )
                                                or (txt[afterPos] == ".")
                                            ):
                                                afterPos += 1
                                            valStr = txt[startPos:afterPos]
                                            while (afterPos < len(txt)) and (
                                                (txt[afterPos] == ",")
                                                or (txt[afterPos] == "[")
                                                or (txt[afterPos] == "]")
                                            ):
                                                afterPos += 1
                                        index += 1
                if self.clkSet != 0:
                    # we should check iDM clock and correct it in case out of sync
                    # accept self.clkSet as max. deviation, if bigger, correct clock, if tooooo big, generate error message and do not touch

                    # Developer info: Since HA decided to have only UIC time internally, all easy python local timestamp functions are destroyed
                    # Thanks community for this crazy decision. Python would offer UTC on all locals, but they know everything better and destroyed it.
                    # Due to that, the defined a buggy dt helper, which should do the trick to have actual local time
                    # However only 50% of it is working and instead of converting a UTC time to local with dt_util.as_local() it just adds the timezone in the end, but not coverts the time
                    # Luckily the dt_util.now seems to work and actually return the time properly. Cross fingers this will stay like this ...

                    if dt_util.now().hour == self.clkSetHour:
                        if not self.clkCheckSetToday:
                            time.sleep(
                                0.4
                            )  # relax a little bit to avoid idm heatpump web overloads
                            _LOGGER.info("Checking for time sync needs ..")
                            response = self.session.get(
                                self.idmInfoUrl,
                                headers=addHeader,
                                timeout=self._timeout,
                            )
                            compareTime = dt_util.now()  # store compare time as close as possible after receiving data
                            if response.status_code == 200:
                                txt = response.text
                                startPos = txt.find('"datetime":"')
                                if startPos != -1:
                                    idmTime = txt[startPos + 12 : startPos + 31]
                                    dtIdm = datetime.strptime(
                                        idmTime, "%Y-%m-%d %H:%M:%S"
                                    )
                                    delta = abs(
                                        (
                                            dtIdm - compareTime.replace(tzinfo=None)
                                        ).total_seconds()
                                    )  # we need to remove the local string, because the dtIdm object do not have it as well
                                    if (
                                        delta > (60 * 35)
                                    ):  # if time difference is more than 35 minutes, something is very wrong, do not touch ...
                                        _LOGGER.warning(
                                            "Timesync: Detected a very big time difference! Adjust iDM clock manually before autosync keeps it in sync"
                                            + "Detected deviation: "
                                            + str(round(delta / 60, 2))
                                            + " minutes; Max. allowed are 35 minutes."
                                        )

                                    elif delta > (self.clkSet + 0.5):
                                        # deviation is bigger than acceptable, therefore start correction now...
                                        _LOGGER.info(
                                            " .. Timesync actually needed! Diff: "
                                            + str(round(delta, 2))
                                        )
                                        time.sleep(0.4)
                                        setIdmTime = (
                                            dt_util.now() + timedelta(seconds=2)
                                        )  # emperical tests showed, adding 2 seconds give most accurate results
                                        setDateData = (
                                            self.idmSettime_HTTP_PUT_Str
                                            + setIdmTime.strftime(
                                                "%Y-%m-%dT%H:%M:%S.%f"
                                            )[:-3]
                                            + 'Z"}'
                                        )
                                        htPut = self.session.put(
                                            self.idmDataUrl,
                                            setDateData,
                                            headers=postIDMHeader,
                                            timeout=self._timeout,
                                        )
                                        if htPut.status_code != 200:
                                            _LOGGER.warning(
                                                ".. Timesync received unexpected response code, did not work! Code: "
                                                + str(htPut.status_code)
                                            )
                                        afterPos = htPut.text.find('"status": "OK"')
                                        if afterPos == -1:
                                            _LOGGER.warning(
                                                ".. Timesync received unexpected answer, may not work: Answer: "
                                                + htPut.text
                                            )
                                            # log warning, timesync received unexpected result, may not working
                                    else:
                                        _LOGGER.info(
                                            " .. Timesync not needed! Diff: "
                                            + str(round(delta, 2))
                                        )

                            self.clkCheckSetToday = True
                    else:
                        self.clkCheckSetToday = False

            return answerData  # return collected answer to caller

        except requests.RequestException as e:
            ## redo login with pin and csrf token extraction
            _LOGGER.warning("Exception during data fetch, redoing login" + str(e))
            time.sleep(10)  # relax to avoid idm heatpump web lockout
            result = self.idm_login()  # we do not care about the result here, if it fails we will trzy again next time
            return answerData
        except:
            # unknown exception occured stop task controlled
            _LOGGER.warning(
                "Unknown Exception during data fetch, stopping reading data!"
            )
            return answerData

        return answerData


def blocking_idm_login_function(idm: idmHeatpumpWeb) -> str:
    """Validate the user input allows us to connect."""
    try:
        return idm.idm_login()

    except Exception:
        return "unknown"
    # return "unknown"


def blocking_idm_get_data_function(idm: idmHeatpumpWeb) -> IdmResponseData:
    """Get data from the heatpump web interface."""
    emptyData = IdmResponseData()
    try:
        return idm.get_DataUpdate()

    except Exception:
        return emptyData
    # return emptyData


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
