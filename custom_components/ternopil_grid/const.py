DOMAIN = "ternopil_grid"

# Config / options
CONF_GROUP = "group"

CONF_PING_IP = "ping_ip"
CONF_PING_PORT = "ping_port"
CONF_PING_TIMEOUT = "ping_timeout"
CONF_PING_INTERVAL = "ping_interval"

# Defaults
DEFAULT_GROUP = "1.1"

DEFAULT_PING_IP = "10.248.1.105"
DEFAULT_PING_PORT = 80
DEFAULT_PING_TIMEOUT = 1.0   # seconds
DEFAULT_PING_INTERVAL = 2.0  # seconds

GROUP_OPTIONS = [
    "1.1","1.2","1.3","1.4",
    "2.1","2.2","2.3","2.4",
    "3.1","3.2","3.3","3.4",
    "4.1","4.2","4.3","4.4",
]

ATTRIBUTION = "Data provided by inneti.net"
PLATFORMS = ["sensor", "binary_sensor", "select"]

# Schedule API 
API_URL = "https://api-toe-poweron.inneti.net/api/a_gpv_g"
SCHEDULE_DAYS = 3
