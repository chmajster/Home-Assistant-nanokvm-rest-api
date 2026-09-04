"""Constants for the NanoKVM REST integration."""

from homeassistant.const import Platform

DOMAIN = "nanokvm_rest"
PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]

CONF_BASE_URL = "base_url"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_NAME = "NanoKVM"
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_POWER_PRESS_MS = 800
DEFAULT_FORCE_OFF_MS = 5000

COOKIE_NAME = "nano-kvm-token"
API_TIMEOUT = 10
SECRET_KEY = "nanokvm-sipeed-2024"
