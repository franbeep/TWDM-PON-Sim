### Abstract Classes

import simpy
from attributes import FOO_DELAY
from data import Packet

import manager as Manager
from utils import Event_Type

class Traffic_Generator(object):
    def __init__(self, env, id, distribution, size):
        self.env = env
        self.id = id
        self.dist = distribution # callable
        self.size = size # callable
        self.packets_sent = 0
        self.hold = simpy.Store(self.env) # hold data
        self.trafic_action = env.process(self.trafic_run())

    def trafic_run(self):
        while True:
            while(self.hold == None):
                yield self.env.timeout(FOO_DELAY)
            yield self.env.timeout(self.dist(self)) # distribution time (wait time between calls)
            if(self.hold == None):
                continue
            p = Packet(self.packets_sent, self.size(self), self.id, -1, self.env.now)
            self.hold.put(p)
            self.packets_sent += 1
            Manager.register_event(Event_Type.TG_SentPacket, self.env.now, self.id, p)


class Active_Node(object):
    def __init__(self, env, enabled, consumption_rate, objs, start_time):
        self.env = env
        self.enabled = enabled
        self.consumption_rate = consumption_rate
        self.start_time = start_time
        self.objs = objs # active nodes inside
        self.elapsed_time = 0
        self.total_time = 0.0
        self.obj_sleeping = [] # sleeping objects
        self.an_action = env.process(self.an_run())

    def start(self):
        self.start_time = self.env.now
        self.enabled = True
        for o in self.obj_sleeping:
            o.start()
        self.obj_sleeping = []
        Manager.register_event(Event_Type.AN_Started, self.env.now, self)

    def end(self):
        self.total_time += self.elapsed_time
        self.elapsed_time = 0
        self.enabled = False
        for o in self.objs:
            if(o.enabled is True):
                self.obj_sleeping.append(o)
                o.end()
        Manager.register_event(Event_Type.AN_Ended, self.env.now, self)
        
    def consumption(self):
        total = 0
        for o in self.objs:
            total += o.consumption()
        return total + self.consumption_rate(self) * (self.total_time + self.elapsed_time)

    def an_run(self):
    	# count time
        while(True):
            if(self.enabled):
                self.elapsed_time = self.env.now - self.start_time
            yield self.env.timeout(FOO_DELAY)


class Virtual_Machine(object):
    def func(self, r):
        return r