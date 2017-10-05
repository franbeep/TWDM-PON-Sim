import sim

# seed
sim.random.seed(13)

# environment
env = sim.simpy.Environment()

### topology
antenas = 4
onus = 3
pns = 2
splts = 2
max_frequencies = 10

matrix = [
    [0,4,10000],
    [1,5,10000],
    [2,5,10000],
    [3,6,10000],
    [4,9,10000],
    [5,9,10000],
    [6,10,10000],
    [7,10,10000],
    [9,7,10000],
    [10,8,10000]
]

# create nodes
nodes = sim.create_topology(env, antenas, onus, pns, splts, matrix, max_frequencies,onu_consumption=15, pn_consumption=20, lc_consumption=5)

### rules
nodes[7].end() # node 5 starts offline

# 3/4 antennas offline
nodes[1].end()
nodes[2].end()
nodes[3].end()

# add a Digital Unit with DBA
# def __init_(self, env, node, consumption_rate, min_band, max_frequency, enabled=True):
nodes[8].append_DU(20, nodes[8], -1, enabled=True, vms=[sim.DBA_Assigner(env, nodes[8], 0, 125000, max_frequencies-3)])

# add a Digital Unit to BB processing
nodes[8].append_DU(20, nodes[8], 0, enabled=True, vms=[sim.Foo_BB_VM(env)])

print("\nBegin.\n")

env.run(until=5)

print("\nEnd.\n")





