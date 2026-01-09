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
