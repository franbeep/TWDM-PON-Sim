# OLT or local node (fog) 4
import simpy
import manager as Manager
from abstract_classes import Active_Node
from attributes import FOO_DELAY, LIGHT_SPEED
from utils import dprint, Event_Type

class Processing_Node(Active_Node):
    def __init__(self, env, id, target_up, target_down, consumption_rate, bitRate_up, bitRate_down, distance, enabled=True, DU=[], LC=[]):
        self.env = env
        self.id = id
        self.DU = DU
        self.LC = LC
        self.bitRate_up = bitRate_up
        self.bitRate_down = bitRate_down
        self.res_hold_up = simpy.Resource(self.env, capacity=1)
        self.res_hold_down = simpy.Resource(self.env, capacity=1)
        self.target_up = target_up
        self.target_down = target_down
        self.hold_up = []
        self.hold_down = []
        self.delay_up = distance / float(LIGHT_SPEED)
        Active_Node.__init__(self, env, enabled, consumption_rate, DU + LC, self.env.now)
        self.action = self.env.process(self.run())

    # calculate time required to transfer size in bytes to onu from node
    def time_to_onu(self, size, id_onu, target=None):
        if(target == None):
            target = self
        if(type(target) is Splitter):
            for t in target.target_down:
                delay_acc = self.time_to_onu(size, id_onu, target=t)
                if(delay_acc > 0):
                    return delay_acc + target.delay_up
        elif(type(target) is ONU):
            if(target.id == id_onu):
                return target.delay_up
        else:
            delay_acc = self.time_to_onu(size, id_onu, target=target.target_down)
            if(delay_acc > 0):
                if(target.bitRate_down > 0):
                    delay_acc += (size / (target.bitRate_down / 8))
                if(self != target):
                    delay_acc += target.delay_up
                return delay_acc
        return 0

    # calculate time required to transfer size in bytes from onu to node
    def time_from_onu(self, size, id_onu, target=None):
        if(target == None):
            target = self.target_down # first time
        if(type(target) is Splitter):
            for t in target.target_down:
                delay_acc = self.time_from_onu(size, id_onu, target=t)
                if(delay_acc > 0):
                    return delay_acc + target.delay_up
        elif(type(target) is ONU):
            if(target.id == id_onu):
                if(target.bitRate_up > 0):
                    return target.delay_up + (size / (target.bitRate_up / 8))
                else:
                    return target.delay_up
        else:
            delay_acc = self.time_from_onu(size, id_onu, target=target.target_down)
            if(delay_acc > 0):
                if(target.bitRate_up > 0):
                    delay_acc += (size / (target.bitRate_up / 8))
                return delay_acc + target.delay_up
        return 0

    def attach_DU(self, du, lc):
        if(self.LC[lc].enabled is False):
            self.LC[lc].start()
        self.LC[lc].out = self.DU[du]

    def append_DU(self, du): self.DU.append(du)

    # upstreaming
    def send_up(self, o):
        if(self.target_up != None):
            if(self.bitRate_up > 0):
                total_size = 0
                if(type(o) is list):
                    for k in o:
                        total_size += k.size
                else:
                    total_size = o.size
                yield self.env.timeout(total_size / (self.bitRate_up / 8)) # transmission
            yield self.env.timeout(self.delay_up) # propagation
            dprint(str(self), "finished sending (upstream) obj at", self.env.now, objn=4)
            self.env.process(self.target_up.put(o, up=True))

    # downstreaming
    def send_down(self, o):
        if(self.target_down != None):
            if(self.bitRate_down > 0):
                total_size = 0
                if(type(o) is list):
                    for k in o:
                        total_size += k.size
                else:
                    total_size = o.size
                yield self.env.timeout(total_size / (self.bitRate_down / 8)) # transmission
            yield self.env.timeout(self.target_down.delay_up) # propagation
            dprint(str(self), "finished sending (downstream) obj at", self.env.now, objn=4)
            self.env.process(self.target_down.put(o, down=True))

    def put(self, pkt, down=False, up=False):
        dprint(str(self), "receveid obj", str(pkt), "at", self.env.now, objn=4)
        if(self.enabled):
            if(down):
                with self.res_hold_down.request() as req:
                    yield req
                    self.hold_down.append(pkt)
            if(up):
                with self.res_hold_up.request() as req:
                    yield req
                    self.hold_up.append(pkt)
            Manager.register_event(Event_Type.PN_ReceivedObject, self.env.now, self, pkt)
        else:
            dprint(str(self), "is not enabled at", self.env.now, objn=4)
            if(down):
                self.env.process(self.send_down(pkt))
            if(up):
                self.env.process(self.send_up(pkt))

    def run(self):
        while(True):
            if(self.enabled):
                # if any data received from down
                if(len(self.hold_up) > 0):
                    with self.res_hold_up.request() as req:
                        yield req
                        o = self.hold_up.pop(0)
                        target_lc = None
                        # search correct lc
                        if(len(self.LC) > 0):
                            for l in self.LC:
                                true_object = o
                                if(type(o) is list):
                                    true_object = o[0]
                                if(true_object.freq == l.freq):
                                    target_lc = l
                                    break
                            if(target_lc != None):
                                self.env.process(target_lc.put(o))
                    continue
                # if any data received from up
                if(len(self.hold_down) > 0):
                    with self.res_hold_down.request() as req:
                        yield req
                        dprint(str(self), "is going to send (downstream) at", self.env.now, objn=4)
                        self.env.process(self.send_down(self.hold_down.pop(0)))
                    continue
            yield self.env.timeout(FOO_DELAY)

    def __repr__(self):
        return "Processing Node #{}".\
            format(self.id)

# delayed initialization to circumvent circular dependency
from splitter import Splitter
from onu import ONU