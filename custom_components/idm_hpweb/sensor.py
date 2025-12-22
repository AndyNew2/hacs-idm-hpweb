"""Platform for sensor integration."""

from __future__ import annotations
from datetime import timedelta
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from functools import partial

import async_timeout

from homeassistant.components.light import LightEntity
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

from homeassistant.const import CONF_HOST, CONF_PIN, CONF_TIMEOUT
from homeassistant.util.unit_conversion import UnitOfElectricPotential
from .const import DEF_TIME_BETWEEN_UPDATES, DOMAIN
from .const import DEF_IDM_PIN, CONF_DISPLAY_NAME, CONF_CYCLE_TIME, SIGNAL_IDM_TELEGRAM
from .idmHeatpumpWeb import (
    idmHeatpumpWeb,
    IdmResponseData,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the idM coordinator."""

    idmObj = idmHeatpumpWeb(
        hass,
        config_entry.data[CONF_HOST],
        config_entry.data[CONF_PIN],
        config_entry.data[CONF_TIMEOUT],
    )

    coordinator = IDM_Coordinator(
        hass,
        config_entry,
        timedelta(seconds=config_entry.data[CONF_CYCLE_TIME]),
        idmObj,
        async_add_entities,
    )
    hass.data[DOMAIN] = coordinator  # probably not needed, but we keep it for now
    await coordinator.async_config_entry_first_refresh()


class IDM_Coordinator(DataUpdateCoordinator):
    """My custom coordinator."""

    def __init__(
        self,
        hass,
        config_entry,
        update_interval,
        my_api: idmHeatpumpWeb,
        async_add_entities: AddEntitiesCallback,
    ) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=DOMAIN,
            config_entry=config_entry,
            update_interval=update_interval,
            always_update=True,
        )
        self.my_api = my_api
        # self._requisteredKeys = [str]   # we can now use _mySensors keys for that
        self._mySensors = {}
        self.async_add_entities = async_add_entities
        self.my_cycleSensor = IDM_SoftwareVersionSensor(self)
        _LOGGER.debug("IDM Coordinator initialized")

    async def _async_setup(self):
        """Handle initial setup tasks."""
        result = await self.my_api.async_idm_async_login()
        # we ignore the result here, errors will be handled during data fetch

        # we add this sensor to drive the update cycle --> all other sensors get their data driven from that update cycle (which is fine, because all data comes together)
        self.async_add_entities([self.my_cycleSensor])
        self._mySensors[self.my_cycleSensor.getIdx()] = self.my_cycleSensor
        # self._requisteredKeys.append(self.my_cycleSensor.getIdx())

        # we add two very popular sensors here directly, the rest is added, when data is received
        # It would not be needed, but prevents having no sensors at all at the beginning
        entity_description = SENSORS.get("B32")
        if entity_description:
            self._mySensors["B32"] = IDM_Entity(self, "B32", entity_description)
            self.async_add_entities([self._mySensors["B32"]])
            # self._requisteredKeys.append("B32")

        entity_description = SENSORS.get("B33")
        if entity_description:
            self._mySensors["B33"] = IDM_Entity(self, "B33", entity_description)
            self.async_add_entities([self._mySensors["B33"]])
            # self._requisteredKeys.append("B33")

        _LOGGER.debug("IDM Coordinator setup complete")

    async def _async_update_data(self):
        """Fetch data from API endpoint."""

        try:
            # Note: asyncio.TimeoutError and aiohttp.ClientError are already
            # handled by the data update coordinator.
            async with async_timeout.timeout(self.config_entry.data[CONF_TIMEOUT] + 1):
                data: IdmResponseData = await self.my_api.async_idm_async_get_data()

                for i in range(data.lenResp()):
                    (key, answer) = data.getResp(i)

                    # if key not in self._requisteredKeys:
                    if key not in self._mySensors:
                        entity_description = SENSORS.get(key)
                        if entity_description:
                            # self.async_add_entities(
                            #    [IDM_Entity(self, key, entity_description)]
                            # )
                            # self._requisteredKeys.append(key)
                            self._mySensors[key] = IDM_Entity(
                                self, key, entity_description
                            )
                            self.async_add_entities([self._mySensors[key]])
                            _LOGGER.debug("Added new sensor for key %s", key)
                        else:
                            _LOGGER.debug(
                                "Small warning! No sensor description found for key %s",
                                key,
                            )

                    sensor = self._mySensors.get(key)
                    if sensor:
                        if sensor.enabled:
                            sensor.setValue(answer)
                            sensor.async_write_ha_state()  # even value not changed, we need to inform HA to avoid stale data

                    # if key == self.my_cycleSensor.getIdx():
                    #    self.my_cycleSensor.setValue(answer)
                    #    # self.my_cycleSensor.async_write_ha_state()
                    # else:
                    #    async_dispatcher_send(
                    #        self.hass, SIGNAL_IDM_TELEGRAM, key, answer
                    #    )

                if data.lenResp() == 0:
                    _LOGGER.warning("No data received from iDM Heatpump")

                _LOGGER.debug(
                    "IDM Data update complete. Found: %d items", data.lenResp()
                )
                return ""
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}") from err


SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="software_version",
        translation_key="software_version",
    ),
    SensorEntityDescription(
        key="regler_online",
        translation_key="regler_online",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
    ),
    SensorEntityDescription(
        key="runtime_nb_1",
        translation_key="runtime_nb_1",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
    ),
    SensorEntityDescription(
        key="switch_cycles_nb_1",
        translation_key="switch_cycles_nb_1",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="runtime_nb_2",
        translation_key="runtime_nb_2",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
    ),
    SensorEntityDescription(
        key="switch_cycles_nb_2",
        translation_key="switch_cycles_nb_2",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="runtime_heating",
        translation_key="runtime_heating",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
    ),
    SensorEntityDescription(
        key="runtime_cooling",
        translation_key="runtime_cooling",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
    ),
    SensorEntityDescription(
        key="runtime_hotwater",
        translation_key="runtime_hotwater",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
    ),
    SensorEntityDescription(
        key="runtime_defrosting",
        translation_key="runtime_defrosting",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
    ),
    # Input, Output and Sensor values
    SensorEntityDescription(
        key="B32",
        translation_key="outdoor_temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B33",
        translation_key="flow_temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B34",
        translation_key="return_temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B48",
        translation_key="water_temp_top",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B41",
        translation_key="water_temp_bottom",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B53",
        translation_key="flow_temp_heatcircuit_c",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B71",
        translation_key="hotgas_temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B37",
        translation_key="airsource_temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B79",
        translation_key="vaporize_start_temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B78",
        translation_key="vaporize_pressure",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B78v",
        translation_key="vaporize_temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B86v",
        translation_key="condense_temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B86",
        translation_key="condense_pressure",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B87",
        translation_key="liquid_temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="board_temperature",
        translation_key="board_temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="B2",
        translation_key="flowmeter",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="battery_voltage_central_unit",
        translation_key="voltage_mainboard",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=2,
    ),
    # Digital Inputs
    SensorEntityDescription(
        key="external_request",
        translation_key="external_trigger",
    ),
    SensorEntityDescription(
        key="ext_switch_heating_cooling",
        translation_key="ext_trig_heat_cool",
    ),
    SensorEntityDescription(
        key="ew_evu_lock_contact",
        translation_key="ewu_evu_lock_contact",
    ),
    SensorEntityDescription(
        key="B15",
        translation_key="problem_eheat",
    ),
    SensorEntityDescription(
        key="B5",
        translation_key="dewpoint_protection_active",
    ),
    SensorEntityDescription(
        key="ext_hotwater_signal",
        translation_key="ext_trig_hotwater",
    ),
    SensorEntityDescription(
        key="B10",
        translation_key="problem_high_pressure",
    ),
    SensorEntityDescription(
        key="M73#1",
        translation_key="flow_pumpe_active",
    ),
    # Analog Outputs
    SensorEntityDescription(
        key="M73#2",
        translation_key="flow_pumpe_speed",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=0,
    ),
    SensorEntityDescription(
        key="M13",
        translation_key="fan_speed",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="ainout_80_81",
        translation_key="ainout_80_81",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="ainout_82_83",
        translation_key="ainout_82_83",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="ainout_84_85",
        translation_key="ainout_84_85",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="ainout_86_87",
        translation_key="ainout_86_87",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="ainout_88_89",
        translation_key="ainout_88_89",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
    ),
    SensorEntityDescription(
        key="ainout_180_181",
        translation_key="ainout_180_181",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=2,
    ),
    # Digital Outputs
    SensorEntityDescription(
        key="M73#3",
        translation_key="flow_pumpe_actstate",
    ),
    SensorEntityDescription(
        key="M51",
        translation_key="4_way_valve_circut1",
    ),
    SensorEntityDescription(
        key="M31",
        translation_key="flowpump_circuit_a",
    ),
    SensorEntityDescription(
        key="M33",
        translation_key="flowpump_circuit_c",
    ),
    SensorEntityDescription(
        key="M43",
        translation_key="mixer_circuit_c",
    ),
    SensorEntityDescription(
        key="M64",
        translation_key="hotwater_circulation_pump",
    ),
    SensorEntityDescription(
        key="E31",
        translation_key="siphon_heating",
    ),
    SensorEntityDescription(
        key="e_heater_1kw_on",
        translation_key="e_heater_1kw_on",
    ),
    SensorEntityDescription(
        key="e_heater_2kw_on",
        translation_key="e_heater_2kw_on",
    ),
    SensorEntityDescription(
        key="e_heater_3kw_on",
        translation_key="e_heater_3kw_on",
    ),
    SensorEntityDescription(
        key="M61",
        translation_key="valve_heating_cooling",
    ),
    SensorEntityDescription(
        key="M62",
        translation_key="valve_warm_cold",
    ),
    SensorEntityDescription(
        key="M63",
        translation_key="value_heating_hotwater",
    ),
    # idm Service Parameter
    SensorEntityDescription(
        key="super_heating_1",
        translation_key="super_heating_1",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="sub_cooling",
        translation_key="sub_cooling",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="valve_position",
        translation_key="valve_position",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="valve_pos_sub_cool",
        translation_key="valve_pos_sub_cool",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="valve_pos_evdmini",
        translation_key="valve_pos_evdmini",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="%",
        suggested_display_precision=1,
    ),
)

SENSORS = {desc.key: desc for desc in SENSOR_TYPES}


class IDM_SoftwareVersionSensor(CoordinatorEntity, SensorEntity):
    """We need one standard sensor to drive the update cycle."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    counter = 0

    def __init__(self, coordinator):
        """Initialize the sensor."""
        super().__init__(coordinator)
        # self.idx = idx  # Index to identify the sensor (index string)
        self._async_remove_dispatcher = None
        self.entity_description = SENSORS.get("software_version")
        self.idx = self.entity_description.key
        devId = coordinator.config_entry.data[CONF_DISPLAY_NAME]
        self._attr_unique_id = f"{devId}_{self.entity_description.translation_key}"
        # self.data = ""  # set initial value to empty string

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Here you can extract data from the coordinator and update the sensor's state
        self.update()
        self.async_write_ha_state()

    def setValue(self, val: str) -> None:
        """Set the value of the sensor."""
        # self.data = val
        self._attr_native_value = val

    def getIdx(self) -> str:
        """Get the index of the sensor."""
        return self.idx

    def update(self) -> None:
        # all handeld by setValue, we do not need to do anything here
        self.counter += 1  # just to make validation happy
        # self._attr_native_value = "exampleVersion" + str(self.counter)


class IDM_Entity(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, coordinator, idx, entity_description):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.idx = idx  # Index to identify the sensor (index string)
        self._async_remove_dispatcher = None
        self.entity_description = entity_description
        devId = coordinator.config_entry.data[CONF_DISPLAY_NAME]
        self._attr_unique_id = f"{devId}_{entity_description.translation_key}"
        self._attr_native_value = (
            "0"  # initial value to avoid number errors for temp sensors
        )
        # self.data = (
        #    "0"  # set initial value to 0 to avoid number errors for temp sensors
        # )

    def setValue(self, val: str) -> None:
        """Set the value of the sensor."""
        self._attr_native_value = val

    def getIdx(self) -> str:
        """Get the index of the sensor."""
        return self.idx


# We now directly set the value in setValue, so no need for dispatcher, should be much faster


#    async def async_added_to_hass(self) -> None:
#        """Run when entity about to be added to hass."""
#
#        @callback
#        def handle_telegram(idx, data):
#            """Update attributes from last received data for this object."""
#            if self.idx != idx:
#                return
#            if self.data == data:  # nothing change, no update needed
#                return
#            self.data = data
#            self.async_write_ha_state()

#        self._async_remove_dispatcher = async_dispatcher_connect(
#            self.hass, SIGNAL_IDM_TELEGRAM, handle_telegram
#        )

#    async def async_will_remove_from_hass(self) -> None:
#        """Run when entity will be removed from hass."""
#        if self._async_remove_dispatcher:
#            self._async_remove_dispatcher()

# @property
# def native_value(self) -> str:
#    """Return the value of the last received telegram."""
#    return self.data


# ---------------- Example sensors for testing purposes only ----------------
class ExampleSensor(SensorEntity):
    """Representation of a Sensor."""

    _attr_name = "iDM Software Version"
    _attr_unique_id = "idm_software_version"
    _attr_has_entity_name = True
    counter = 0
    # _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    # _attr_device_class = SensorDeviceClass.TEMPERATURE
    # _attr_state_class = SensorStateClass.MEASUREMENT

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self.counter += 1
        self._attr_native_value = "exampleVersion" + str(self.counter)


class ExampleSensor2(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    _attr_name = "iDM Test Sensor"
    _attr_unique_id = "idm_testSensor"
    _attr_has_entity_name = True
    counter = 0

    # _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    # _attr_device_class = SensorDeviceClass.TEMPERATURE
    # _attr_state_class = SensorStateClass.MEASUREMENT
    def __init__(self, coordinator, idx):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.idx = idx  # Index to identify the sensor

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Here you can extract data from the coordinator and update the sensor's state
        self.update()
        self.async_write_ha_state()

    def update(self) -> None:
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        """
        self.counter += 1
        strCount = self.counter
        if strCount > 20:
            strCount = 20
        if self.counter > 40:
            self.counter = 0
        self._attr_native_value = "SensorVal " + str(strCount)
