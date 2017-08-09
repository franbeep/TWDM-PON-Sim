import sim

sim.random.seed(20)

#### 1 - Antenna

print("\t1 - Teste somente Antenna")

# Antenna (self, env, id, out, consumption_rate, bitRate, distance, enabled=True, rate_dist=rrh_default_dist):

env = sim.simpy.Environment()
ant = sim.Antenna(env, 0, None, 1, 10, 1000)
env.run(until=5) # roda por 5 seg
print()