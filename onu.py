# ONU 32
import simpy
from abstract_classes import Active_Node
from attributes import FOO_DELAY, LIGHT_SPEED
from utils import dprint
from dba import Request, Grant
from data import Packet

class ONU(Active_Node):
    self.total_hold_size = 0
    self.ack = 0
    self.hold_up = []
    self.hold_down = []
    self.grants = []
    self.requests = []
    self.timer = []
    self.waiting = False
    self.resent = 1
    self.reset_timer = False
    self.request_counting = 0

    def __init__(self, env, id, target_up, target_down, consumption, cellsite, bitRate_up, bitRate_down, distance, enabled=True, freq=-1, threshold=0):
        self.env = env
        self.id = id
        self.freq = freq
        self.target_up = target_up
        if(target_down == None):
            self.target_down = []
        else:
            self.target_down = target_down
        self.cellsite = cellsite # id cellsite
        self.delay_up = distance / float(LIGHT_SPEED)
        self.res_hold_up = simpy.Resource(self.env, capacity=1)
        self.res_hold_down = simpy.Resource(self.env, capacity=1)
        self.res_grants = simpy.Resource(self.env, capacity=1)
        self.res_requests = simpy.Resource(self.env, capacity=1)

        self.bitRate_up = bitRate_up
        self.bitRate_down = bitRate_down
        self.threshold = threshold

        Active_Node.__init__(self, env, enabled, consumption, [], self.env.now)
        self.action = env.process(self.run())

    def round_trip_time(self):
        total = 0
        target = self
        while(not (isinstance(target, Processing_Node) and target.enabled) ):
            total += target.delay_up
            target = target.target_up
        total += target.time_to_onu(0, self.id)
        dprint(str(self), "calculated RTT:", total, objn=32)
        return total

    def end(self):
        self.hold_up = []
        self.hold_down = []
        self.grants = []
        self.requests = []
        self.timer = []
        Active_Node.end(self)

    # receive new data to upstream/downstream it
    def put(self, pkt, down=False, up=False):
        dprint(str(self), "receveid obj", str(pkt), "at", self.env.now, objn=32)
        if(self.enabled):
            if(down):
                # one grant
                if(type(pkt) is Grant and pkt.onu == self.id):
                    self.reset_timer = True
                    self.resent = 1
                    with self.res_grants.request() as req:
                        yield req
                        self.grants.append(pkt)
                # many grants
                elif(type(pkt) is list and type(pkt[0]) is Grant and pkt[0].onu == self.id_sender):
                    self.reset_timer = True
                    self.resent = 1
                    with self.res_grants.request() as req:
                        yield req
                        for g in pkt:
                            self.grants.append(g)
                # data
                elif(type(pkt) is Packet):
                    with self.res_hold_down.request() as req:
                        yield req
                        self.hold_down.append(pkt)

            elif(up):
                with self.res_hold_up.request() as req:
                    yield req
                    self.hold_up.append(pkt)
                    self.total_hold_size += pkt.size
                    if(self.total_hold_size > self.threshold):
                        self.env.process(self.gen_request())

    # generate a request
    def gen_request(self):
        dprint(str(self), "is generating a request at", self.env.now, objn=32)
        with self.res_requests.request() as req:
            yield req
            self.requests.append(Request(self.request_counting, self.id, -1, self.total_hold_size, self.ack))
            if(not self.waiting):
                self.timer.append(self.round_trip_time() * 2 * self.resent) # 2 x RTT
                self.reset_timer = False
            self.request_counting += 1

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
            dprint(str(self), "finished sending (upstream) obj at", self.env.now, objn=32)
            self.env.process(self.target_up.put(o, up=True))

    # downstreaming
    def send_down(self, o):
        if(self.target_down != None):
            sorted(self.target_down, key=lambda target: target.delay_up)
            counted = 0
            for t in self.target_down:
                additional_time = 0
                if(bitRate_down > 0):
                    total_size = 0
                    if(type(o) is list):
                        for k in o:
                            total_size += k.size
                    else:
                        total_size = o.size
                    additional_time = total_size / (self.bitRate_down / 8)                    
                yield self.env.timeout(additional_time + t.delay_up - counted) # errado?
                counted = additional_time + t.delay_up
                dprint(str(self), "finished sending (downstream) obj at", self.env.now, objn=32)
                self.env.process(t.put(o, down=True))
             # transmission
            yield self.env.timeout(self.target_down.delay_up) # propagation
            self.env.process(self.target_down.put(o, down=True))

    # use the grant(s) you received
    def use_grant(self, grant):
        if(self.ack < grant.ack):
            # update ack
            self.ack = grant.ack

        to_wait = grant.init_time - self.env.now
        if(to_wait < 0):
            # negative time to wait
            dprint(str(self), "is going to discard grant, reason: negative wait time; at", self.env.now, objn=32)
            self.env.process(self.gen_request())

        data_to_transfer = []
        with self.res_hold_up.request() as req:
            yield req
            total = 0
            while(len(self.hold_up) > 0):
                p = self.hold_up.pop(0)
                if(total + p.size > grant.size):
                    self.hold_up.insert(0, p)
                    break
                data_to_transfer.append(p)
                total += p.size
            self.total_hold_size -= total
        dprint(str(self), "plans to send", str(data_to_transfer), "with a hold of", str(self.hold_up), "and grant of", str(grant) ,"at", self.env.now, objn=32)
        if(len(data_to_transfer) < 1):
            # data is empty! return grant and data
            with self.res_hold_up.request() as req:
                for d in reversed(data_to_transfer):
                    self.hold_up.insert(0, d)
            with self.res_grants.request() as req:
                self.grants.insert(0, grant)
            return
        for d in data_to_transfer: # (self, id, size, src, dst, init_time):
            d.src = self.id
            d.waited_time = self.env.now - d.init_time
            d.freq = grant.freq

        self.freq = grant.freq # tune ONU to freq
        dprint(str(self), "is going to wait", str(to_wait), "at", self.env.now, objn=32)
        yield self.env.timeout(to_wait)
        yield self.env.process(self.send_up(data_to_transfer))
        dprint(str(self), "sent data at", self.env.now, objn=32)
            

    # in case grant hasn't come
    def set_timer(self):
        to_wait = self.timer.pop(0)
        self.waiting = True
        yield self.env.timeout(to_wait)
        if(self.reset_timer):
            dprint(str(self), "Discarding timer: Grant received already at", self.env.now, objn=32)
        else:
            dprint(str(self), "Resending request... at", self.env.now, objn=32)
            self.resent *= 2
            self.env.process(self.gen_request())
        self.waiting = False

    # actions
    def run(self):
        while True:
            if(self.enabled):
                if(len(self.requests) > 0): # if you have requests to send
                    with self.res_requests.request() as req:
                        yield req
                        dprint(str(self), "is sending a request at", self.env.now, objn=32)
                        self.env.process(self.send_up(self.requests.pop(0)))

                if(len(self.grants) > 0 and len(self.hold_up) > 0): # if you got grants
                    with self.res_grants.request() as req:
                        yield req
                        dprint(str(self), "is going to use a grant at", self.env.now, objn=32)
                        sorted(self.grants, key=lambda grant: grant.init_time) # sort grants, lower to greater time
                        self.env.process(self.use_grant(self.grants.pop(0)))

                if(len(self.hold_down) > 0): # if you got downstreaming data
                    with self.res_hold_down as req:
                        yield req
                        dprint(str(self), "is going to send (downstream) at", self.env.now, objn=32)
                        self.env.process(self.send_down(self.hold_down.pop(0)))

                if(len(self.timer) > 0):
                    if(self.reset_timer):
                        self.timer = []
                    else:
                        dprint(str(self), "is setting timer to resend request at", self.env.now, objn=32)
                        self.env.process(self.set_timer())

            yield self.env.timeout(FOO_DELAY)

    def __repr__(self):
        return "ONU #{}".\
            format(self.id)

# delayed initialization to circumvent circular dependency
from processing_node import Processing_Node
from splitter import Splitter