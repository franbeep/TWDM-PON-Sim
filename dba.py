### DBA 
import simpy
from data import Packet
from abstract_classes import Active_Node, Virtual_Machine
from attributes import FOO_DELAY, DBA_IPACT_DEFAULT_BANDWIDTH
from utils import dprint

from manager import Manager
from utils import Event_Type

class Request(Packet):
    def __init__(self, id, id_sender, freq, bandwidth, ack):
        self.id_sender = id_sender
        self.freq = freq
        self.bandwidth = bandwidth
        self.ack = ack
        Packet.__init__(self, id, 0, id_sender, -1, -1)

    def __repr__(self):
        return "Request [id:{},id_sender:{},freq:{},bandwidth:{},ack:{}]".\
            format(self.id, self.id_sender, self.freq, self.bandwidth, self.ack)

class Grant(Packet):
    def __init__(self, onu, init_time, size, freq, ack):
        self.onu = onu
        self.ack = ack
        Packet.__init__(self, -1, size, -1, -1, init_time, freq=freq)

    def __repr__(self):
        return "Grant [onu:{},init_time:{},size:{},freq:{},ack:{}]".\
            format(self.onu, self.init_time, self.size, self.freq, self.ack)

class DBA_IPACT(Active_Node, Virtual_Machine):
    self.counting = False
    self.discarded_requests = 0
    self.duplicated_requests = 0
    self.onus = [] # onus "connected"
    self.acks = {}
    self.bandwidth_used = []

    def __init__(self, env, node, consumption_rate, freq, bandwidth, busy, delay=0, enabled=True):
        self.env = env
        self.node = node
        self.delay = delay # delay to execute
        self.freq = freq
        self.bandwidth = bandwidth
        self.busy = busy
        self.free_time = self.env.now
        Active_Node.__init__(self, env, enabled, consumption_rate, [], self.env.now)
        self.action = self.env.process(self.run())

    def update_bandwidth(self):
        # update bandwidth used
        while(len(self.bandwidth_used) > 0 and self.env.now - self.bandwidth_used[0][2] > 1):
            dprint(str(self), "is desassociating with ONU #", self.bandwidth_used.pop(0)[0], objn=64)
        # update onus connected
        self.onus = []
        for b in self.bandwidth_used:
            self.onus.append(b[0])

    def bandwidth_available(self):
        self.update_bandwidth()
        # check bandwidth
        bandwidth_really_used = 0
        for b in self.bandwidth_used:
            bandwidth_really_used += b[1]
        dprint(str(self), "bandwidth available:", self.bandwidth - bandwidth_really_used, objn=64)

        return self.bandwidth - bandwidth_really_used

    # override function
    def end(self):
        self.onus = []
        self.acks = {}
        Active_Node.end(self)

    def associate_onu(self, r):
        self.onus.append(r.id_sender)
        self.acks[r.id_sender] = r.ack

    def desassociate_onu(self, onu):
        self.onus.remove(onu)
        del self.acks[onu]

    def func(self, r):
        with self.busy.request() as req: # semaphore
            yield req
            if(type(r) is Request and r.id_sender in self.onus):
                # process request
                dprint("Receiving", str(r), "at", self.env.now, objn=64)
                if(r.ack != self.acks[r.id_sender]): # not aligned acks!
                    dprint(str(self), "received duplicated request at", self.env.now, objn=64)
                    self.duplicated_requests += 1
                    return r
                # aligned acks
                time_to = self.node.time_to_onu(0, r.id_sender)
                time_from = self.node.time_from_onu(r.bandwidth, r.id_sender)

                available_band = self.bandwidth_available()
                if(available_band > 0):
                    # there is bandwidth
                    g = None
                    # generate grant(s)
                    self.acks[r.id_sender] += 1

                    send_time = 0
                    if(self.env.now + time_to > self.free_time):
                        # (possibly) first case
                        send_time = self.env.now + time_to + FOO_DELAY
                    else:
                        # normal case
                        send_time = self.free_time + FOO_DELAY

                    send_size = 0
                    if(available_band >= r.bandwidth):
                        dprint(str(self), "has enough bandwidth for request at", self.env.now, objn=64)
                        send_size = r.bandwidth
                    else:
                        dprint(str(self), "hasn't enough bandwidth for request, generating max band at", self.env.now, objn=64)
                        send_size = available_band

                    g = Grant(r.id_sender, send_time, send_size, self.freq, self.acks[r.id_sender])
                    dprint(str(self), "generated", str(g), "at", self.env.now, objn=64)
                    self.free_time = send_time + time_from

                    self.env.process(self.node.send_down(g))
                    Manager.register_event(Event_Type.DBA_SentGrant, self.env.now, self.freq)
                    self.bandwidth_used.append((g.onu, g.size, g.init_time, g.init_time + time_from))
                    dprint("Bandwidth available:", self.bandwidth_available(), "at", self.env.now, objn=64)
                    yield self.env.timeout(self.delay)
                    self.counting = True
                    return None # return none

                else:
                    # no bandwidth
                    # activate random local PN
                    dprint(str(self), "has no bandwidth at", self.env.now, objn=64)
                    if(len(self.node.local_nodes) > 0):
                        # activate more-local PN
                        dprint(str(self), "is activating a more local node randomly at", self.env.now, objn=64)
                        self.discarded_requests += 1
                        node = self.node.local_nodes.pop()
                        node.start()
                    else:
                        # no more local nodes!
                        dprint(str(self), "is discarding request: no bandwidth available at", self.env.now, objn=64)
                        self.discarded_requests += 1
            else:
                # pass along to another dba
                dprint(str(self),"is passing along object", str(r), "at", self.env.now, objn=64)
                return r

    def run(self):
        while True:
            if(self.enabled and self.counting):
                self.update_bandwidth()
                if(len(self.onus) < 0):
                    dprint(str(self), "is going to hibernate at", self.env.now, objn=64)
                    self.counting = False
                    self.node.LC[self.freq+1].end() # suspend LC linked to this VPON
                    self.end() # suspend this VPON
            yield self.env.timeout(FOO_DELAY)

    def __repr__(self):
        return "DBA IPACT [freq:{},free_time:{}]".\
            format(self.freq, self.free_time)

class DBA_Assigner(Active_Node, Virtual_Machine):
    self.available_freq = 0
    self.dbas = []
    
    def __init__(self, env, node, consumption_rate, max_frequency, enabled=True, delay=0):
        self.env = env
        self.node = node
        self.max_frequency = max_frequency
        self.delay = delay
        self.busy = simpy.Resource(self.env, capacity=1)
        self.dba_busy = simpy.Resource(self.env, capacity=1)
        Active_Node.__init__(self, env, enabled, consumption_rate, [], self.env.now)

    def func(self, o):
        if(type(o) is Request):
            with self.busy.request() as req: # semaphore
                dprint(str(self), "received", str(o), "at", self.env.now, objn=128)
                # search request's dba (if possible)
                target_dba = None
                yield self.env.timeout(self.delay)

                for d in self.dbas:
                    if(o.id_sender in d.onus): # found!
                        dprint(str(self) + ": this ONU has already a DBA", objn=128)
                        return o
                    if(d.bandwidth_available() > 0):
                        if(target_dba is None):
                            target_dba = d
                        else:
                            if(target_dba.bandwidth_available() < r.bandwidth and target_dba.bandwidth_available() < d.bandwidth_available()):
                                target_dba = d

                # not fonud! create/assign new DBA
                dprint(str(self) + ": this ONU hasn't a DBA", objn=128)
                if(target_dba == None):
                    if(len(self.node.LC) > self.available_freq+1):
                        # create, if possible
                        dprint(str(self) + ": Creating DBA at", self.env.now, objn=128)
                        target_dba = DBA_IPACT(self.env, self.node, 0, self.available_freq, DBA_IPACT_DEFAULT_BANDWIDTH, self.dba_busy) # DBA_IPACT_DEFAULT_BANDWIDTH
                        lc = self.node.LC[self.available_freq+1]
                        if(lc.enabled is False):
                            lc.start()
                        if(lc.out == None):
                            lc.out = self.node.DU[1] # guessed baseband DU
                        self.available_freq += 1
                        target_dba.associate_onu(o)
                        yield self.env.process(self.node.DU[0].append_vm(target_dba))
                        self.dbas.append(target_dba)
                    else:
                        dprint(str(self.node), "has no bandwidth at", self.env.now, objn=128)
                else:
                    dprint(str(self) + ": Assigning DBA", objn=128)
                    # assign
                    if(target_dba.enabled is False):
                        target_dba.start()
                    target_dba.associate_onu(o)
        return o

    def __repr__(self):
        return "DBA Assigner #{}".\
            format(self.node.id)