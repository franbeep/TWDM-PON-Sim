  ### DBA 
import simpy
from data import Packet
from abstract_classes import Active_Node, Virtual_Machine
from attributes import FOO_DELAY, DBA_IPACT_DEFAULT_BANDWIDTH
from utils import dprint

import manager as Manager
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
    def __init__(self, env, node, consumption_rate, freq, bandwidth, busy, delay=0, enabled=True):
        self.env = env
        self.node = node
        self.delay = delay # delay to execute
        self.freq = freq
        self.bandwidth = bandwidth
        self.busy = busy
        self.free_time = self.env.now
        self.counting = False
        self.onus = [] # onus "connected"
        self.acks = {}
        self.bandwidth_used = []
        Active_Node.__init__(self, env, enabled, consumption_rate, [], self.env.now)
        self.action = self.env.process(self.run())

    def end(self):
        self.onus = []
        self.acks = {}
        Active_Node.end(self)

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

    def associate_onu(self, r):
        self.onus.append(r.id_sender)
        self.acks[r.id_sender] = r.ack

    def func(self, r):
        if(not(type(r) is Request and r.id_sender in self.onus)):
            # pass along to another dba
            dprint(str(self),"is passing along object", str(r), "at", self.env.now, objn=64)
            return r
        with self.busy.request() as req:
            yield req
            # process request
            dprint(str(self), "received", str(r), "at", self.env.now, objn=64)
            if(r.ack != self.acks[r.id_sender]): # not aligned acks!
                dprint(str(self), ": duplicated request at", self.env.now, objn=64)
                Manager.register_event(Event_Type.DBA_DuplicatedRequest, self.env.now, self, r)
                return None
            time_to = self.node.time_to_onu(0, r.id_sender)
            time_from = self.node.time_from_onu(r.bandwidth, r.id_sender)
            available_band = self.bandwidth_available()
            # no bandwidth
            if(available_band <= 0):
                # activate random local PN
                dprint(str(self), "has no bandwidth: discarding request at", self.env.now, objn=64)
                Manager.register_event(Event_Type.DBA_DiscardedRequest, self.env.now, self, r)
                if(len(self.node.local_nodes) > 0):
                    dprint(str(self), "is activating a more local node (randomly) at", self.env.now, objn=64)
                    node = self.node.local_nodes.pop()
                    while(node.enabled and self.node.local_nodes > 0): node = self.node.local_nodes.pop()
                    if(not (node is None)): node.start()
                return None
            self.acks[r.id_sender] += 1
            send_time = 0
            if(self.env.now + time_to > self.free_time): send_time = self.env.now + time_to + FOO_DELAY
            else:                                        send_time = self.free_time + FOO_DELAY
            send_size = 0
            if(available_band >= r.bandwidth): send_size = r.bandwidth
            else:                              send_size = available_band
            g = Grant(r.id_sender, send_time, send_size, self.freq, self.acks[r.id_sender])
            dprint(str(self), "generated", str(g), "at", self.env.now, objn=64)
            self.free_time = send_time + time_from
            self.env.process(self.node.send_down(g))
            Manager.register_event(Event_Type.DBA_SentGrant, self.env.now, self, g)
            self.bandwidth_used.append((g.onu, g.size, g.init_time, g.init_time + time_from))
            dprint("Bandwidth available:", self.bandwidth_available(), "at", self.env.now, objn=64)
            yield self.env.timeout(self.delay)
            self.counting = True
            return None # return none

    def run(self):
        while True:
            if(self.enabled and self.counting):
                self.update_bandwidth()
                if(len(self.onus) < 0):
                    dprint(str(self), "is going to hibernate at", self.env.now, objn=64)
                    self.counting = False
                    self.node.LC[self.freq+1].end() # suspend LC linked to this VPON
                    self.end() # suspend this VPON
                    Manager.register_event(Event_Type.DBA_Hibernated, self.env.now, self)
            yield self.env.timeout(FOO_DELAY)

    def __repr__(self):
        return "DBA IPACT [freq:{},free_time:{}]".\
            format(self.freq, self.free_time)

class DBA_Assigner(Active_Node, Virtual_Machine):
    def __init__(self, env, node, consumption_rate, max_frequency, enabled=True, delay=0):
        self.env = env
        self.node = node
        self.max_dba_count = max_frequency
        self.delay = delay
        self.available_freq = 1
        self.dbas = []
        self.busy = simpy.Resource(self.env, capacity=1)
        self.dba_busy = simpy.Resource(self.env, capacity=1)
        Active_Node.__init__(self, env, enabled, consumption_rate, [], self.env.now)

    def func(self, r):
        if(not (type(r) is Request)):
            return r
        with self.busy.request() as req:
            yield req
            # set dba for request
            dprint(str(self), "received", str(r), "at", self.env.now, objn=128)
            target_dba = None
            for d in self.dbas:
                if(r.id_sender in d.onus):
                    dprint(str(self) + ": this ONU has already a DBA at", self.env.now, objn=128)
                    return r
                if(target_dba is None): target_dba = d
                elif(target_dba.bandwidth_available() < r.bandwidth and \
                     target_dba.bandwidth_available() < d.bandwidth_available()): target_dba = d
            if(target_dba == None):
                if(len(self.dbas) == self.max_dba_count): # no VPON with enough bandwidth
                    Manager.register_event(Event_Type.DBA_DiscardedRequest, self.env.now, self, r)
                    return None 
                dprint(str(self) + ": Creating DBA at", self.env.now, objn=128)
                target_dba = DBA_IPACT(self.env, self.node, 0, self.available_freq, DBA_IPACT_DEFAULT_BANDWIDTH, self.dba_busy)
                lc = self.node.LC[self.available_freq]
                if(lc.enabled is False):
                    lc.start()
                if(lc.out == None):
                    lc.out = self.node.DU[1] # guessed baseband DU
                self.available_freq += 1
                target_dba.associate_onu(r)
                yield self.env.process(self.node.DU[0].append_vm(target_dba))
                self.dbas.append(target_dba)
                Manager.register_event(Event_Type.DBA_Created_VPON, self.env.now, self, r, target_dba)
            else:
                dprint(str(self) + ": Assigning DBA", objn=128)
                if(target_dba.enabled is False):
                    target_dba.start()
                target_dba.associate_onu(r)
            yield self.env.timeout(self.delay)
        return r

    def __repr__(self):
        return "DBA Assigner #{}".\
            format(self.node.id)