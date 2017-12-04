import manager as Manager
from attributes import *
from utils import End_Sim, DEBUG_SET, simlog


# start simulation function
def run(env, ending_type=End_Sim.ByTimeCount, until=0, debug=0):
    # define debug level
    if(debug > 0):
        val = debug
        while(not (val in [2 ** x for x in range(PRINTABLE_CLASS_NUMBERS)])):
            val -= 1
        while(debug):
            debug -= val
            if debug < 0: debug += val
            else: DEBUG_SET.append(val)
            val = int(val / 2)
    # start!
    # env.run(until=Manager.create_end_event(env, ending_type, until))
    env.run(until=until)
    for e in Manager.events:
        print(e)

# clean current simulation function
def clean():
    # close log file
    simlog.close()
    # reset Manager
    Manager.events = []
    Manager.generated_requests = 0
    Manager.lost_requests = 0
    Manager.duplicated_requests = 0
    Manager.generated_grants = 0
    Manager.lost_grants = 0

