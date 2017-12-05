### Manager of simulation events

from attributes import FOO_DELAY
from utils import End_Sim, dprint, Event_Type

events = []

generated_requests = 0
discarded_requests = 0
duplicated_requests = 0
generated_grants = 0
discarded_grants = 0

# create event that ends simulation
def create_end_event(env, ending_type, qty):
    def count_request(q):
        while(generated_requests < q):
            yield env.timeout(FOO_DELAY)
        dprint("Simulation ended after", q, "requests.")
    def count_grant(q):
        while(generated_grants < q):
            yield env.timeout(FOO_DELAY)
        dprint("Simulation ended after", q, "seconds.")

    if(ending_type == End_Sim.ByRequestCount):
        return env.process(count_request(qty))
    elif(ending_type == End_Sim.ByTimeCount):
        return qty
    elif(ending_type == End_Sim.ByGrantCount):
        return env.process(count_grant(qty))

# register event that happened
def register_event(etype, time, *obj):
    global generated_requests
    global discarded_requests
    global duplicated_requests
    global generated_grants
    global discarded_grants

    events.append((etype.name, time, obj))
    if(etype is Event_Type.DBA_DiscardedRequest):
        discarded_requests += 1
    elif(etype is Event_Type.DBA_DuplicatedRequest):
        duplicated_requests += 1
    elif(etype is Event_Type.ONU_DiscardedGrant):
        discarded_grants += 1
    elif(etype is Event_Type.ONU_GenerateRequest):
        generated_requests += 1
    elif(etype is Event_Type.DBA_SentGrant):
        generated_grants += 1

# schedule a event to start in [time] seconds
def schedule_event(env, time, func):
    def delegator(env, time, func):
        yield env.timeout(time)
        func()
    env.process(delegator(env, time, func))