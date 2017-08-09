import sim

sim.random.seed(20)

#### 4 - Processing Node

print("\t4 - Teste Antenna ligada a ONU ligada a Processing_Node ligado a Splitter")

# Processing Node (self, env, id, consumption_rate, target_up, target_down, bitRate_up, bitRate_down, distance, enabled=True, DU=[], LC=[])

env = sim.simpy.Environment()
ant = sim.Antenna(env, 0, None, 1, 250, 1000)
splt = sim.Splitter(env, 0, None, None, 500)
onu = sim.ONU(env, 0, None, None, 1, None, 250, 250, 1000)
pn  = sim.Processing_Node(env, 0, 1, None, None, 250, 250, 1250)

ant.target_up = onu
onu.target_up = pn
pn.target_up = splt

env.run(until=5)
print()