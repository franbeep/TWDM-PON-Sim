import sim

# seed
sim.random.seed(13)

# environment
env = sim.simpy.Environment()

# writer
# packet_w = Writer("packet_", start="# id src init_time waited_time freq processed_time\n")

# default values
sim.tg_default_size = lambda x: 5000
sim.tg_default_dist = lambda x: 1
sim.DBA_IPACT_default_bandwidth = 5000
# constants

# topology
antenas = 3
onus = 2
pns = 2
splts = 1
max_freqs = 10

matrix = [
    [0,3,10000],
    [1,3,9000],
    [2,4,13000],
    [3,5,500],
    [4,7,25000],
    [5,7,23000],
    [7,6,8000]
]

# nodes
nodes = sim.create_topology(env, antenas, onus, pns, splts, matrix, max_freqs)

# rules
nodes[5].end() # node 5 starts offline

nodes[0].end() # antenna 0 starts offline
nodes[1].end() # antenna 1 starts offline


print("Begin.")

env.run(until=5)

print("End.")
