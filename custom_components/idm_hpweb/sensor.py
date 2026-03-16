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
    UnitOfPower,
    UnitOfEnergy,
)
from homeassistant.core import HomeAssistant, HomeAssistantError, ServiceCall
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
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import (
    async_dispatcher_connect,
    async_dispatcher_send,
)

from homeassistant.const import CONF_HOST, CONF_PIN, CONF_TIMEOUT
from homeassistant.util.unit_conversion import UnitOfElectricPotential
from .const import DEF_TIME_BETWEEN_UPDATES, DOMAIN
from .const import (
    DEF_IDM_PIN, CONF_DISPLAY_NAME, CONF_CYCLE_TIME,
    DEF_DEVICE_NAME, CONF_STAT_DIV, CONF_CLK_SET,
    CONF_CLK_HOUR, CONF_CLK_HOUR_DEFAULT,
    SERVICE_SET_HEATPUMP_OPERATION_MODE,
    SERVICE_SET_HOT_WATER_MIN_TEMP,
    SERVICE_SET_HOT_WATER_MAX_TEMP,
    SERVICE_SET_HOT_WATER_BOOST_TEMP,
    SERVICE_SET_HOT_WATER_LEGIONELLA_FCT,
    SERVICE_SET_HOT_WATER_LEGIONELLA_TEMP,
    SERVICE_SET_HOT_WATER_LEGIONELLA_DAYS,
    SERVICE_SET_HOT_WATER_TRIGGER_GENERATION,
    SERVICE_SET_MAX_HEATING_POWER,
    SERVICE_SET_MIN_HEATING_POWER,
    SERVICE_SET_MAX_HOT_WATER_POWER,
    SERVICE_SET_DEFROST_POWER,
    SERVICE_SET_MAX_FLOWPUMP_POWER,
    SERVICE_SET_MIN_FLOWPUMP_POWER,
    SERVICE_SET_HOT_WATER_BIVALENCE_SWITCHTEMP,
)
from .idmHeatpumpWeb import (
    idmHeatpumpWeb,
    IdmResponseData,
)

from .idmHeatpumpWeb_Services import idmHeatpumpWebService

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the idM coordinator."""

    stat_divider = config_entry.data.get(CONF_STAT_DIV, 0)  # we added this parameter later, therefore needs proper default
    clk_set = config_entry.data.get(CONF_CLK_SET, 0)  # this is a further added parameter, therfore a default needs to be defined here.
    clk_set_hour = config_entry.data.get(CONF_CLK_HOUR, CONF_CLK_HOUR_DEFAULT)  # default defined in const, but logic is same as above

    idmObj = idmHeatpumpWebService(
        hass,
        config_entry.data[CONF_HOST],
        config_entry.data[CONF_PIN],
        config_entry.data[CONF_TIMEOUT],
        stat_divider, clk_set, clk_set_hour,
    )
    coordinator = IDM_Coordinator(
        hass, config_entry,
        timedelta(seconds=config_entry.data[CONF_CYCLE_TIME]),
        idmObj, async_add_entities,
    )
    hass.data[DOMAIN] = coordinator  # probably not needed, but we keep it for now
    await coordinator.async_config_entry_first_refresh()

    async def handle_set_heatpump_operation_mode(call: ServiceCall):
        """Handle the service call to set heatpump operation mode."""
        mode: str = call.data.get("operation_mode", "automatic")

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_HEATPUMP_OPERATION_MODE}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged" )

        result = await idmObj.async_set_heatpump_operation_mode(mode)
        if not result:
            raise HomeAssistantError( f"Failed to set heatpump operation mode to {mode}", translation_domain=DOMAIN, translation_key="set_heatpump_operation_mode_failed" )
    hass.services.async_register( domain=DOMAIN, service=SERVICE_SET_HEATPUMP_OPERATION_MODE, service_func=handle_set_heatpump_operation_mode )

    async def handle_set_hot_water_min_temp(call: ServiceCall):
        """Handle the service call to set hot water minimum temperature."""
        temp: int = call.data.get("min_temp", 40.0)

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_HOT_WATER_MIN_TEMP}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged")
        result = await idmObj.async_set_hot_water_min_temp(temp)
        if not result:
            raise HomeAssistantError( f"Failed to set hot water minimum temperature to {temp}°C", translation_domain=DOMAIN )
    hass.services.async_register(domain=DOMAIN, service=SERVICE_SET_HOT_WATER_MIN_TEMP, service_func=handle_set_hot_water_min_temp)

    async def handle_set_hot_water_max_temp(call: ServiceCall):
        """Handle the service call to set hot water maximum temperature."""
        temp: int = call.data.get("max_temp", 50)

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_HOT_WATER_MAX_TEMP}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged")
        result = await idmObj.async_set_hot_water_max_temp(temp)
        if not result:
            raise HomeAssistantError( f"Failed to set hot water maximum temperature to {temp}°C", translation_domain=DOMAIN )
    hass.services.async_register(domain=DOMAIN, service=SERVICE_SET_HOT_WATER_MAX_TEMP, service_func=handle_set_hot_water_max_temp)

    async def handle_set_hot_water_boost_temp(call: ServiceCall):
        """Handle the service call to set hot water boost temperature."""
        temp: int = call.data.get("boost_temp", 60)

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_HOT_WATER_BOOST_TEMP}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged")
        result = await idmObj.async_set_hot_water_boost_temp(temp)
        if not result:
            raise HomeAssistantError( f"Failed to set hot water boost temperature to {temp}°C", translation_domain=DOMAIN )
    hass.services.async_register(domain=DOMAIN, service=SERVICE_SET_HOT_WATER_BOOST_TEMP, service_func=handle_set_hot_water_boost_temp)

    async def handle_set_hot_water_legionella_fct(call: ServiceCall):
        """Handle the service call to set hot water legionella function."""
        legio_fct: str = call.data.get("legionella_fct", "off")

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_HOT_WATER_LEGIONELLA_FCT}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged")
        result = await idmObj.async_set_hot_water_legionella_fct(legio_fct)
        if not result:
            raise HomeAssistantError( f"Failed to set hot water legionella function to {legio_fct}", translation_domain=DOMAIN )
    hass.services.async_register(domain=DOMAIN, service=SERVICE_SET_HOT_WATER_LEGIONELLA_FCT, service_func=handle_set_hot_water_legionella_fct)

    async def handle_set_hot_water_legionella_temp(call: ServiceCall):
        """Handle the service call to set hot water legionella temperature."""
        temp: int = call.data.get("legionella_temp", 67)

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_HOT_WATER_LEGIONELLA_TEMP}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged")
        result = await idmObj.async_set_hot_water_legionella_temp(temp)
        if not result:
            raise HomeAssistantError( f"Failed to set hot water legionella temperature to {temp}°C", translation_domain=DOMAIN )
    hass.services.async_register(domain=DOMAIN, service=SERVICE_SET_HOT_WATER_LEGIONELLA_TEMP, service_func=handle_set_hot_water_legionella_temp)

    async def handle_set_hot_water_legionella_days(call: ServiceCall):
        """Handle the service call to set hot water legionella days interval."""
        days: int = call.data.get("legionella_days", 7)

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_HOT_WATER_LEGIONELLA_DAYS}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged")
        result = await idmObj.async_set_hot_water_legionella_days(days)
        if not result:
            raise HomeAssistantError( f"Failed to set hot water legionella days interval to {days} days", translation_domain=DOMAIN )
    hass.services.async_register(domain=DOMAIN, service=SERVICE_SET_HOT_WATER_LEGIONELLA_DAYS, service_func=handle_set_hot_water_legionella_days)

    async def handle_set_hot_water_trigger_generation(call: ServiceCall):
        """Handle the service call to trigger hot water generation."""
        generation_mode: str = call.data.get("hot_water_trigger_gen", "not defined")

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_HOT_WATER_TRIGGER_GENERATION}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged")

        result = await idmObj.async_set_hot_water_trigger_generation(generation_mode)
        if not result:
            raise HomeAssistantError( f"Failed to trigger hot water generation with mode {generation_mode}", translation_domain=DOMAIN )
    hass.services.async_register( domain=DOMAIN, service=SERVICE_SET_HOT_WATER_TRIGGER_GENERATION, service_func=handle_set_hot_water_trigger_generation )

    ### Advanced Services ###
    async def handle_set_max_heating_power(call: ServiceCall):
        """Handle the service call to set max heating power."""
        max_power: int = call.data.get("max_heating_power", 65)

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_MAX_HEATING_POWER}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged" )
        acknowledge_adv = call.data.get("acknowledge_risk_advanced")
        if acknowledge_adv is not True:
            raise HomeAssistantError( f"Must acknowledge advanced risk to call {SERVICE_SET_MAX_HEATING_POWER}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged_advanced" )

        result = await idmObj.async_set_max_heating_power(max_power)
        if not result:
            raise HomeAssistantError( f"Failed to set max heating power to {max_power}%", translation_domain=DOMAIN)
    hass.services.async_register(domain=DOMAIN, service=SERVICE_SET_MAX_HEATING_POWER, service_func=handle_set_max_heating_power)

    async def handle_set_min_heating_power(call: ServiceCall):
        """Handle the service call to set min heating power."""
        min_power: int = call.data.get("min_heating_power", 30)

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_MIN_HEATING_POWER}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged" )
        acknowledge_adv = call.data.get("acknowledge_risk_advanced")
        if acknowledge_adv is not True:
            raise HomeAssistantError( f"Must acknowledge advanced risk to call {SERVICE_SET_MIN_HEATING_POWER}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged_advanced" )

        result = await idmObj.async_set_min_heating_power(min_power)
        if not result:
            raise HomeAssistantError( f"Failed to set min heating power to {min_power}%", translation_domain=DOMAIN)
    hass.services.async_register(domain=DOMAIN, service=SERVICE_SET_MIN_HEATING_POWER, service_func=handle_set_min_heating_power)

    async def handle_set_max_hot_water_power(call: ServiceCall):
        """Handle the service call to set max hot water power."""
        max_power: int = call.data.get("max_hot_water_power", 65)

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError(
                f"Must acknowledge risk to call {SERVICE_SET_MAX_HOT_WATER_POWER}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged" )
        acknowledge_adv = call.data.get("acknowledge_risk_advanced")
        if acknowledge_adv is not True:
            raise HomeAssistantError( f"Must acknowledge advanced risk to call {SERVICE_SET_MAX_HOT_WATER_POWER}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged_advanced" )

        result = await idmObj.async_set_max_hot_water_power(max_power)
        if not result:
            raise HomeAssistantError( f"Failed to set max hot water power to {max_power}%", translation_domain=DOMAIN )
    hass.services.async_register(domain=DOMAIN, service=SERVICE_SET_MAX_HOT_WATER_POWER, service_func=handle_set_max_hot_water_power)

    async def handle_set_defrost_power(call: ServiceCall):
        """Handle the service call to set defrost power."""
        power: int = call.data.get("defrost_power", 65)

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_DEFROST_POWER}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged" )
        acknowledge_adv = call.data.get("acknowledge_risk_advanced")
        if acknowledge_adv is not True:
            raise HomeAssistantError( f"Must acknowledge advanced risk to call {SERVICE_SET_DEFROST_POWER}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged_advanced" )

        result = await idmObj.async_set_defrost_power(power)
        if not result:
            raise HomeAssistantError( f"Failed to set defrost power to {power}%", translation_domain=DOMAIN )
    hass.services.async_register(domain=DOMAIN, service=SERVICE_SET_DEFROST_POWER, service_func=handle_set_defrost_power)

    async def handle_set_max_flowpump_power(call: ServiceCall):
        """Handle the service call to set max flowpump power."""
        max_power: int = call.data.get("max_flowpump_power", 80)

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_MAX_FLOWPUMP_POWER}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged" )
        acknowledge_adv = call.data.get("acknowledge_risk_advanced")
        if acknowledge_adv is not True:
            raise HomeAssistantError( f"Must acknowledge advanced risk to call {SERVICE_SET_MAX_FLOWPUMP_POWER}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged_advanced" )

        result = await idmObj.async_set_max_flowpump_power(max_power)
        if not result:
            raise HomeAssistantError( f"Failed to set max flowpump power to {max_power}%", translation_domain=DOMAIN )
    hass.services.async_register(domain=DOMAIN, service=SERVICE_SET_MAX_FLOWPUMP_POWER, service_func=handle_set_max_flowpump_power)

    async def handle_set_min_flowpump_power(call: ServiceCall):
        """Handle the service call to set min flowpump power."""
        min_power: int = call.data.get("min_flowpump_power", 60)

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_MIN_FLOWPUMP_POWER}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged" )
        acknowledge_adv = call.data.get("acknowledge_risk_advanced")
        if acknowledge_adv is not True:
            raise HomeAssistantError( f"Must acknowledge advanced risk to call {SERVICE_SET_MIN_FLOWPUMP_POWER}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged_advanced" )

        result = await idmObj.async_set_min_flowpump_power(min_power)
        if not result:
            raise HomeAssistantError( f"Failed to set min flowpump power to {min_power}%", translation_domain=DOMAIN )
    hass.services.async_register(domain=DOMAIN, service=SERVICE_SET_MIN_FLOWPUMP_POWER, service_func=handle_set_min_flowpump_power)

    async def handle_set_hot_water_bivalence_switchtemp(call: ServiceCall):
        """Handle the service call to set hot water bivalence switch temperature."""
        temp: int = call.data.get("bivalence_switch_temp", 50)

        acknowledge = call.data.get("acknowledge_risk")
        if acknowledge is not True:
            raise HomeAssistantError( f"Must acknowledge risk to call {SERVICE_SET_HOT_WATER_BIVALENCE_SWITCHTEMP}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged" )
        acknowledge_adv = call.data.get("acknowledge_risk_advanced")
        if acknowledge_adv is not True:
            raise HomeAssistantError( f"Must acknowledge advanced risk to call {SERVICE_SET_HOT_WATER_BIVALENCE_SWITCHTEMP}", translation_domain=DOMAIN, translation_key="risk_not_acknowledged_advanced" )

        result = await idmObj.async_set_hot_water_bivalence_switchtemp(temp)
        if not result:
            raise HomeAssistantError( f"Failed to set hot water bivalence switch temperature to {temp}°C", translation_domain=DOMAIN )
    hass.services.async_register(domain=DOMAIN, service=SERVICE_SET_HOT_WATER_BIVALENCE_SWITCHTEMP, service_func=handle_set_hot_water_bivalence_switchtemp)

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
            async with async_timeout.timeout(self.config_entry.data[CONF_TIMEOUT]+2):  # add 2 seconds for additional data frames which might be needed
                data: IdmResponseData = await self.my_api.async_idm_async_get_data()

                for i in range(data.lenResp()):
                    (key, answer) = data.getResp(i)

                    if key not in self._mySensors:
                        entity_description = SENSORS.get(key)
                        if entity_description:
                            self._mySensors[key] = IDM_Entity(self, key, entity_description)
                            self.async_add_entities([self._mySensors[key]])
                            _LOGGER.debug("Added new sensor for key %s", key)
                        else:
                            _LOGGER.warning("Small warning! No sensor description found for key %s",key)

                    sensor = self._mySensors.get(key)
                    if sensor:
                        if sensor.enabled:
                            sensor.setValue(answer)
                            sensor.async_write_ha_state()  # even value not changed, we need to inform HA to avoid stale data

                if data.lenResp() == 0: _LOGGER.warning("No data received from iDM Heatpump")

                _LOGGER.debug("IDM Data update complete. Found: %d items", data.lenResp())
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
        key="B38",
        translation_key="heatstore_temperature",
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
    SensorEntityDescription( key="M73#3", translation_key="flow_pumpe_actstate" ),
    SensorEntityDescription( key="M51", translation_key="4_way_valve_circut1" ),
    SensorEntityDescription( key="M31", translation_key="flowpump_circuit_a" ),
    SensorEntityDescription( key="M33", translation_key="flowpump_circuit_c" ),
    SensorEntityDescription( key="M43", translation_key="mixer_circuit_c" ),
    SensorEntityDescription( key="M64", translation_key="hotwater_circulation_pump" ),
    SensorEntityDescription( key="E31", translation_key="siphon_heating" ),
    SensorEntityDescription( key="e_heater_1kw_on", translation_key="e_heater_1kw_on" ),
    SensorEntityDescription( key="e_heater_2kw_on", translation_key="e_heater_2kw_on" ),
    SensorEntityDescription( key="e_heater_3kw_on", translation_key="e_heater_3kw_on" ),
    SensorEntityDescription( key="M61", translation_key="valve_heating_cooling" ),
    SensorEntityDescription( key="M62", translation_key="valve_warm_cold" ),
    SensorEntityDescription( key="M63", translation_key="value_heating_hotwater" ),
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
    # idm PV Parameter (if PV is configured in iDM)
    SensorEntityDescription(
        key="cur_exp_power_heating",
        translation_key="cur_exp_power_heating",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="cur_exp_power_cooling",
        translation_key="cur_exp_power_cooling",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="cur_exp_power_hotwater",
        translation_key="cur_exp_power_hotwater",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="cur_el_power",
        translation_key="cur_el_power",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=1,
    ),
    # statistics values if statistics are enabled
    # first with runtime values
    SensorEntityDescription(
        key="stat_runtime_total_heating",
        translation_key="stat_runtime_total_heating",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_runtime_total_cooling",
        translation_key="stat_runtime_total_cooling",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_runtime_total_hotwater",
        translation_key="stat_runtime_total_hotwater",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_runtime_total_defrost",
        translation_key="stat_runtime_total_defrost",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_runtime_cur_year_heating",
        translation_key="stat_runtime_cur_year_heating",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_runtime_cur_year_cooling",
        translation_key="stat_runtime_cur_year_cooling",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_runtime_cur_year_hotwater",
        translation_key="stat_runtime_cur_year_hotwater",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_runtime_cur_year_defrost",
        translation_key="stat_runtime_cur_year_defrost",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=6,
    ),
    # now stats with generated heat
    SensorEntityDescription(
        key="stat_genheat_total_heating",
        translation_key="stat_genheat_total_heating",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:heat-wave",
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_genheat_total_cooling",
        translation_key="stat_genheat_total_cooling",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:snowflake",
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_genheat_total_hotwater",
        translation_key="stat_genheat_total_hotwater",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:heat-wave",
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_genheat_total_defrost",
        translation_key="stat_genheat_total_defrost",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:snowflake-melt",
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_genheat_cur_year_heating",
        translation_key="stat_genheat_cur_year_heating",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:heat-wave",
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_genheat_cur_year_cooling",
        translation_key="stat_genheat_cur_year_cooling",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:snowflake",
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_genheat_cur_year_hotwater",
        translation_key="stat_genheat_cur_year_hotwater",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:heat-wave",
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_genheat_cur_year_defrost",
        translation_key="stat_genheat_cur_year_defrost",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        icon="mdi:snowflake-melt",
        suggested_display_precision=6,
    ),
    # now stats with electrical power consumption
    SensorEntityDescription(
        key="stat_elcons_total_heating",
        translation_key="stat_elcons_total_heating",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_elcons_total_cooling",
        translation_key="stat_elcons_total_cooling",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_elcons_total_hotwater",
        translation_key="stat_elcons_total_hotwater",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_elcons_total_defrost",
        translation_key="stat_elcons_total_defrost",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_elcons_cur_year_heating",
        translation_key="stat_elcons_cur_year_heating",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_elcons_cur_year_cooling",
        translation_key="stat_elcons_cur_year_cooling",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_elcons_cur_year_hotwater",
        translation_key="stat_elcons_cur_year_hotwater",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=6,
    ),
    SensorEntityDescription(
        key="stat_elcons_cur_year_defrost",
        translation_key="stat_elcons_cur_year_defrost",
        state_class=SensorStateClass.TOTAL,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=6,
    ),
    # heatpump status values
    SensorEntityDescription(
        key="flow_temp_set_hc_A",
        translation_key="flow_temp_set_hc_a",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="flow_temp_set_hc_B",
        translation_key="flow_temp_set_hc_b",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="flow_temp_set_hc_C",
        translation_key="flow_temp_set_hc_c",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="flow_temp_set_hc_D",
        translation_key="flow_temp_set_hc_d",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="flow_temp_set_hc_E",
        translation_key="flow_temp_set_hc_e",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="flow_temp_set_hc_F",
        translation_key="flow_temp_set_hc_f",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="flow_temp_set_hc_G",
        translation_key="flow_temp_set_hc_g",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SensorEntityDescription(
        key="cur_el_power_pre",
        translation_key="cur_el_power_pre",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=4,
    ),
    SensorEntityDescription( key="mode_heatcirc_A", translation_key="mode_heatcirc_a" ),
    SensorEntityDescription( key="mode_heatcirc_B", translation_key="mode_heatcirc_b" ),
    SensorEntityDescription( key="mode_heatcirc_C", translation_key="mode_heatcirc_c" ),
    SensorEntityDescription( key="mode_heatcirc_D", translation_key="mode_heatcirc_d" ),
    SensorEntityDescription( key="mode_heatcirc_E", translation_key="mode_heatcirc_e" ),
    SensorEntityDescription( key="mode_heatcirc_F", translation_key="mode_heatcirc_f" ),
    SensorEntityDescription( key="mode_heatcirc_G", translation_key="mode_heatcirc_g" ),
    SensorEntityDescription(
        key="cur_heat_power",
        translation_key="cur_heat_power",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        suggested_display_precision=1,
    ),
    SensorEntityDescription( key="heatpump_op_mode", translation_key="heatpump_op_mode" ),
    SensorEntityDescription( key="heatpump_compressor", translation_key="heatpump_compressor", icon="mdi:play" ),
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
        self._async_remove_dispatcher = None
        self.entity_description = SENSORS.get("software_version")
        self.idx = self.entity_description.key
        devId = coordinator.config_entry.data[CONF_DISPLAY_NAME]
        self._attr_unique_id = f"{devId}_{self.entity_description.translation_key}"

        hostName = coordinator.my_api.get_host()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hostName)},
            manufacturer="iDM",
            model="Navigator 2.0 Web",
            sw_version="",
            model_id="Host: "+hostName,
        )
        # self._attr_device_info = DeviceInfo( identifiers={(DOMAIN, devId)}, name=DEF_DEVICE_NAME)

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # Here you can extract data from the coordinator and update the sensor's state
        self.update()
        self.async_write_ha_state()

    def setValue(self, val: str) -> None:
        """Set the value of the sensor."""
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

        hostName = coordinator.my_api.get_host()
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, hostName)},
            manufacturer="iDM",
            model="Navigator 2.0 Web",
            sw_version="",
            model_id="Host: "+hostName,
        )
        # self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, devId)}, name=DEF_DEVICE_NAME)

    def setValue(self, val: str) -> None:
        """Set the value of the sensor."""
        self._attr_native_value = val

    def getIdx(self) -> str:
        """Get the index of the sensor."""
        return self.idx
