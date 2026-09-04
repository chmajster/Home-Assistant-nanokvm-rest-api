"""Constants for the NanoKVM REST integration."""

from homeassistant.const import Platform

DOMAIN = "nanokvm_rest"
PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]

CONF_BASE_URL = "base_url"
CONF_VERIFY_SSL = "verify_ssl"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_FORCE_OFF_MS = "force_off_ms"

DEFAULT_NAME = "NanoKVM"
DEFAULT_SCAN_INTERVAL = 30
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 3600

DEFAULT_POWER_PRESS_MS = 800
DEFAULT_FORCE_OFF_MS = 5000
MIN_FORCE_OFF_MS = 1000
MAX_FORCE_OFF_MS = 10000

COOKIE_NAME = "nano-kvm-token"
API_TIMEOUT = 10
SECRET_KEY = "nanokvm-sipeed-2024"
