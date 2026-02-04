"""Constants for the iDM Heatpump Web integration."""

from datetime import timedelta

DOMAIN = "idm_hpweb"
CONF_DISPLAY_NAME = "display_name"
CONF_CYCLE_TIME = "CYCLE_TIME"
CONF_STAT_DIV = "STATISTICS_DIV"
CONF_CLK_SET = "CLOCK_SET_DEVIATION"
CONF_CLK_HOUR = "CLOCK_SET_HOUR"
CONF_CLK_HOUR_DEFAULT = 2
DEF_DEVICE_NAME = "iDMwb"
DEF_MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=2)
DEF_TIME_BETWEEN_UPDATES = timedelta(seconds=10)
DEF_IDM_PIN = "4444"

# Services
SERVICE_SET_HEATPUMP_OPERATION_MODE = "set_heatpump_operation_mode"
SERVICE_SET_HOT_WATER_MIN_TEMP = "set_hot_water_min_temp"
SERVICE_SET_HOT_WATER_MAX_TEMP = "set_hot_water_max_temp"
SERVICE_SET_HOT_WATER_BOOST_TEMP = "set_hot_water_boost_temp"
SERVICE_SET_HOT_WATER_LEGIONELLA_FCT = "set_hot_water_legionella_fct"
SERVICE_SET_HOT_WATER_LEGIONELLA_TEMP = "set_hot_water_legionella_temp"
SERVICE_SET_HOT_WATER_LEGIONELLA_DAYS = "set_hot_water_legionella_days"
SERVICE_SET_HOT_WATER_TRIGGER_GENERATION = "set_hot_water_trigger_generation"
