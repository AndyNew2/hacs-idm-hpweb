"""Constants for the iDM Heatpump Web integration."""

from datetime import timedelta

DOMAIN = "idm_hpweb"
CONF_DISPLAY_NAME = "display_name"
CONF_CYCLE_TIME = "CYCLE_TIME"
SIGNAL_IDM_TELEGRAM = "idm_telegram"
DEF_MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=2)
DEF_TIME_BETWEEN_UPDATES = timedelta(seconds=10)
DEF_IDM_PIN = "4444"
