import sim

# seed
sim.random.seed(13)

# environment
env = sim.simpy.Environment()

# default values

# constants

# topology
antenas = 3
onus = 2
pns = 2
splts = 1

matrix = [
    [0,3,10000],
    [1,3,9000],
    [2,4,13000],
    [3,5,500],
    [4,7,25000],
    [5,7,23000],
    [7,6,18000]
]

# nodes
nodes = sim.create_topology(env, antenas, onus, pns, splts, matrix)

# rules
nodes[5].end() # node 5 starts offline

print("Begin.")

env.run(until=6)

print("End.")
