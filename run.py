import sim

env = sim.simpy.Environment()
sim.random.seed(20)


print("test começa:")
# class Antenna(Traffic_Generator, Active_Node):
# def __init__(self, env, id, users, bitRate, out, distance, enabled=True, rate_dist=rrh_default_dist, consumption_rate=0):

# class ONU(Active_Node):
# def __init__(self, env, id, target, consumption, cellsite, bitRate, rrhs, enabled=True, freq=-1, distance=0, total_distance=0, threshold=0):

onu = sim.ONU(env, 0, None, 13, None, 10, None, enabled=False)

# ant1 = sim.Antenna(env, 0, 10, None, 1000, consumption_rate=1)

env.run(until=5)

# print("consumption total = " + str(ant1.consumption()))

print("finished test!")
