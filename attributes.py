### Default attributes

import random

# default traffic generator size:
TG_DEFAULT_SIZE = lambda x: 50
# default traffic generator distribution:
TG_DEFAULT_DIST = lambda x: random.expovariate(10)
# default DBA bandwidth:
DBA_IPACT_DEFAULT_BANDWIDTH = 1250000 # 1.25 Gb/s, bandwidth for each frequency/vpon
# default Antenna consumption:
ANT_CONSUMPTION = lambda x: 0
# default ONU consumption:
ONU_CONSUMPTION = lambda x: 0
# default Processing Node consumption:
PN_CONSUMPTION = lambda x: 0
# default LineCard consumption:
LC_CONSUMPTION = lambda x: 0
# default Digital Unit consumption:
DU_COMSUMPTION = lambda x: 0
# default ONU threshold:
ONU_THRESHOLD = 0
# default ONU bit rate downstreaming:
ONU_BITRATE_DOWN = 0
# default ONU bit rate upstreaming:
ONU_BITRATE_UP = 0
# default Processing Node downstreaming:
PN_BITRATE_DOWN = 0
# default Processing Node upstreaming:
PN_BITRATE_UP = 0

# Constants

# Light Speed:
LIGHT_SPEED = 300000000
# Radio Speed:
ANTENNA_SPEED = 300000000
# interactions delay (to not overload the simulator):
FOO_DELAY = 0.00005 # arbitrary

PRINTABLE_CLASS_NUMBERS = 10