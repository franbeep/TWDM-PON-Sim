import sim

sim.random.seed(20)

#### 2 - Splitters

print("\t2 - Teste Antenna ligada a Splitter ligado a Splitter (2 Splitters)")

# Splitter (self, env, id, target_up, target_down, distance_up)

env = sim.simpy.Environment()
splt1 = sim.Splitter(env, 0, None, None, 500)
splt2 = sim.Splitter(env, 0, splt1, None, 500)
ant = sim.Antenna(env, 0, splt2, 1, 100, 1000)
env.run(until=5)
print()