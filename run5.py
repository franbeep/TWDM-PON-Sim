import sim

sim.random.seed(13)

#### 5 - DU + LC + Random VM

print("\t5 - Teste 4 so que com VM Teste instanciado em uma DU no Node (seed 13)")

# Digital_Unit (self, env, id, consumption_rate, node, out, vms=None, enabled=True)
# LineCard (self, env, freq, delay=0, out=None, enabled=True, consumption=0)
# DBA_default (self, env, vpons, node, consumption_rate, delay=0, enabled=True)
# Foo_VM (self, env)

env = sim.simpy.Environment()
ant = sim.Antenna(env, 0, None, 1, 250, 1000)
splt = sim.Splitter(env, 0, None, None, 500)
onu = sim.ONU(env, 0, None, None, 1, None, 250, 250, 1000)
pn  = sim.Processing_Node(env, 0, 1, None, None, 250, 250, 1250)

ant.target_up = onu
onu.target_up = pn
pn.target_up = splt

vm = sim.Foo_VM(env)
du = sim.Digital_Unit(env, 0, 1, pn, pn, vms=[vm])
lc = sim.LineCard(env, -1, out=du)

pn.DU = [du]
pn.LC = [lc]

env.run(until=5)
print()