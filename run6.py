import sim

sim.random.seed(13)

#### 6 - DBA

print("\t6 - Teste 5 so que com VM DBA")

# DBA_default (self, env, vpons, node, consumption_rate, delay=0, enabled=True):

env = sim.simpy.Environment()
ant = sim.Antenna(env, 0, None, 1, 250, 1000)
splt = sim.Splitter(env, 0, None, None, 500)
onu = sim.ONU(env, 0, None, None, 1, None, 250, 250, 1000)
pn  = sim.Processing_Node(env, 0, 1, None, None, 250, 250, 1250)

ant.target_up = onu
onu.target_up = pn
pn.target_down = onu

vm = sim.DBA_default(env, pn, 1)
du = sim.Digital_Unit(env, 0, 1, pn, pn, vms=[vm])
lc = sim.LineCard(env, -1, out=du)

pn.DU = [du]
pn.LC = [lc]

env.run(until=5)
