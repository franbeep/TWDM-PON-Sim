import sim

sim.random.seed(20)

#### 3 - ONU

print("\t3 - Teste Antenna ligada a Splitter ligado a ONU ligada a um Splitter (2 Splitters)")

# ONU (self, env, id, target_up, target_down, consumption, cellsite, bitRate_up, bitRate_down, rrhs, enabled=True, freq=-1, distance=0, threshold=0):

env = sim.simpy.Environment()
splt = sim.Splitter(env, 0, None, None, 500)
splt_f = sim.Splitter(env, 0, None, None, 500)
ant = sim.Antenna(env, 0, splt, 1, 100, 1000)
onu = sim.ONU(env, 0, splt_f, splt, 1, None, 100, 100, 1000)

splt.target_up = onu
env.run(until=5)
print()