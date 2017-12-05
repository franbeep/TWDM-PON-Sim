# traffic gen implemented 1
from utils import dprint
from abstract_classes import Traffic_Generator, Active_Node
from attributes import FOO_DELAY, ANTENNA_SPEED, TG_DEFAULT_DIST, TG_DEFAULT_SIZE

import manager as Manager
from utils import Event_Type

class Antenna(Traffic_Generator, Active_Node):
    def __init__(self, env, id, target_up, consumption_rate, bitRate, distance, enabled=True):
        self.env = env
        self.id = id
        self.bitRate = bitRate
        self.target_up = target_up
        self.delay = distance / float(ANTENNA_SPEED)
        Traffic_Generator.__init__(self, self.env, self.id, TG_DEFAULT_DIST, TG_DEFAULT_SIZE)
        Active_Node.__init__(self, self.env, enabled, consumption_rate, [], self.env.now)
        self.action = env.process(self.run())

    def start(self):
        self.hold = simpy.Store(self.env)
        Active_Node.start(self)

    def end(self):
        self.hold = None
        Active_Node.end(self)

    def run(self):
        while(True):
            if(self.enabled):
                pkt = yield self.hold.get() # wait data
                dprint(str(self), "took", str(pkt), "at", self.env.now, objn=1)
                if(self.target_up != None):
                    if(self.bitRate > 0):
                        yield self.env.timeout(pkt.size / (self.bitRate / 8)) # transmission
                    yield self.env.timeout(self.delay) # propagation
                    dprint(str(self), "delivered to", str(self.target_up), "at", self.env.now, objn=1)
                    self.env.process(self.target_up.put(pkt, up=True))
                    Manager.register_event(Event_Type.ANT_SentPacket, self.env.now, self, pkt)
            yield self.env.timeout(FOO_DELAY)

    def __repr__(self):
        return "Antenna #{}".\
            format(self.id)

