from __future__ import annotations

DOMAIN = "ternopil_grid"

# Fixed city: Ternopil (toe-poweron.inneti.net)
DEFAULT_TERNOPIL_CITY_ID = 1032

# Config keys
CONF_CITY_ID = "city_id"
CONF_STREET_ID = "street_id"        # used for debug-key (city_id/street_id)
CONF_STREET_NAME = "street_name"    # shown in UI / entry title
CONF_HOUSE_NUMBER = "house_number"  # informational (used in title)
CONF_GROUP = "group"

# Entity naming
CONF_POWER_SENSOR_NAME = "power_sensor_name"

# Ping / connectivity
CONF_PING_IP = "ping_ip"
CONF_PING_INTERVAL = "ping_interval"
CONF_PING_METHOD = "ping_method"
CONF_PING_PORT = "ping_port"
CONF_PING_TIMEOUT = "ping_timeout"

DEFAULT_NAME = "Ternopil Grid"
DEFAULT_POWER_SENSOR_NAME = "Ternopil Grid Power"

DEFAULT_PING_IP = "1.1.1.1"
DEFAULT_PING_INTERVAL = 10  # seconds
DEFAULT_PING_METHOD = "icmp"
DEFAULT_PING_PORT = 80
DEFAULT_PING_TIMEOUT = 1.0  # seconds

# Outage groups (UI select)
# NOTE: API returns strings like "4.1". Keep this list conservative; user can still type/select later if needed.
GROUP_OPTIONS = [
    "1.1", "1.2",
    "2.1", "2.2",
    "3.1", "3.2",
    "4.1", "4.2",
]
DEFAULT_GROUP = "1.1"

# Data coordinator
DEFAULT_UPDATE_INTERVAL = 300  # seconds
