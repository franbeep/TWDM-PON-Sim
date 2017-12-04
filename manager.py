### Manager of simulation events

from attributes import FOO_DELAY
from utils import End_Sim

past_events = []

generated_requests = 0
lost_requests = 0
duplicated_requests = 0

generated_grants = 0
lost_grants = 0

# create event that ends simulation
def create_end_event(env, ending_type, qty):
	def count_request(q):
		while(generated_requests < q):
			yield FOO_DELAY
	def count_grant(q):
		while(generated_grants < q):
			yield FOO_DELAY
	if(ending_type == End_Sim.ByRequestCount):
		return env.process(count_request(qty))
	elif(ending_type == End_Sim.ByTimeCount):
		return qty
	elif(ending_type == End_Sim.ByGrantCount):
		return env.process(count_grant(qty))

# register event that happened
def register_event(etype, time, *info): past_events.append[(etype.name, time, *info)]

# schedule a event to start in [time] seconds
def schedule_event(env, time, func, *args):
	def delegator(env, time, func, *args):
		yield env.timeout(time)
		func(args)
	env.process(delegator(env, time, func, args))