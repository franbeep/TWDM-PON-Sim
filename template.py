# Template for a simulation

import sim
import topology
import simpy
import random
import utils

# Defines the classes that will be needed to print
# values from 0 to 255, where 0 means nothing and
# 255 means everything.
#
# TABLE:
# 1 - antenna
# 2 - splitter
# 4 - processing node
# 8 - digital unit
# 16 - linecard
# 32 - onu
# 64 - dba slave (vm)
# 128 - dba master (vm)
#
# Example:
# DEBUG = 1+4+16+32 # means that only antennas,
#					# processing nodes, linecards
# 					# and ONUs do print.
DEBUG=0

# seed to pseudo random values
sim.random.seed(13)

# SimPy's simulation environment
env = simpy.Environment()

### Section: default values and constants
sim.TG_DEFAULT_SIZE = lambda x: 5000
sim.TG_DEFAULT_DIST = lambda x: 1
sim.DBA_IPACT_DEFAULT_BANDWIDTH = 5000

### Section: topology
# Dictates the anatomy of the network: which node
# is connected to whom.

antenas = 3
onus = 2
pns = 2
splts = 1
max_freqs = 10

matrix = [
    [0,3,10000],  # antenna (node[0]) connects to ONU (node[3])
    [1,3,9000],   # antenna (node[1]) connects to ONU (node[3])
    [2,4,13000],  # antenna (node[2]) connects to ONU (node[4])
    [3,5,500],    # ONU (node[3]) connects to processing node (node[5])
    [4,7,25000],  # ONU (node[4]) connects to splitter (node[7])
    [5,7,23000],  # processing node (node[5]) connects to onu (node[3])
    [7,6,8000]    # antenna (node[0]) connects to onu (node[3])
]
# obs: in this case, node[5] (processing node) is a local node

# create nodes
nodes = topology.create_topology(env, antenas, onus, pns, \
									splts, matrix, max_freqs)

### Section: rules
# Here should be placed any kind of rule, i.e.,
# extra information that cannot be provided
# before.

# example: node 5 starts offline
nodes[5].end() 
# example: schedule to antenna 0 be disabled in 1 sec
sim.Manager.schedule_event(env, 1, nodes[0].end)

nodes[0].end

# starts simulation and set to end by time count with 3 secs
sim.run(env, ending_type=sim.End_Sim.ByTimeCount, until=3, debug=DEBUG)

# close file descriptors
sim.clean()
