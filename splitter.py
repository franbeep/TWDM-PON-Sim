# passive Splitter 2

from attributes import LIGHT_SPEED
from utils import dprint

import manager as Manager
from utils import Event_Type

class Splitter(object):
    def __init__(self, env, id, target_up, target_down, distance_up):
        self.env = env
        self.id = id
        self.target_up = target_up
        if target_down is None: self.target_down = []
        else: self.target_down = target_down
        self.delay_up = distance_up / float(LIGHT_SPEED)

    def put(self, pkt, down=False, up=False):
        dprint(str(self), "receveid obj", str(pkt), "at", self.env.now, objn=2)
        if(down):
            self.target_down.sort(key=lambda target: target.delay_up)
            counted = 0
            for t in self.target_down:
                yield self.env.timeout(t.delay_up - counted)
                counted = t.delay_up
                self.env.process(t.put(pkt, down=True))
        if(up):
            yield self.env.timeout(self.delay_up)
            self.env.process(self.target_up.put(pkt, up=True))
        Manager.register_event(Event_Type.SPLT_ReceivedObject, self.env.now, self, pkt)


    def __repr__(self):
        return "Splitter #{}".\
            format(self.id)