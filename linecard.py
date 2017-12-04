# linecard attuned to a frequency 16

from abstract_classes import Active_Node
from attributes import LC_CONSUMPTION
from utils import dprint

class LineCard(Active_Node):
    def __init__(self, env, freq, delay=0, out=None, enabled=False, consumption=LC_CONSUMPTION):
        self.env = env
        self.delay = delay
        self.freq = freq
        self.out = out
        Active_Node.__init__(self, env, enabled, consumption, [], self.env.now)

    def put(self, p):
        if(self.out != None and self.enabled == True):
            dprint(str(self), "is pushing", p, "to a DU at", self.env.now, objn=16)
            yield self.env.timeout(self.delay)
            self.env.process(self.out.execute_functions(p))

    def __repr__(self):
        return "LineCard freq:{}".\
            format(self.freq)