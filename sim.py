import simpy
import functools
import random

trafgen_def_dist = functools.partial(random.expovariate, 5.0)
traffic_gen_default_size = 50
Light_Speed         = 210000 # light speed
foo_delay           = 0.0001

# abstract class
class Traffic_Generator(object):
    def __init__(self, env, id, distribution, hold=None):
        self.env              = env
        self.id               = id
        self.dist             = distribution
        self.hold             = hold # armazena os Packets
        self.trafic_action    = env.process(self.trafic_run())
        self.packets_sent     = 0

    def trafic_run(self):
        while True:
            yield self.env.timeout(self.dist()) # tempo de espera
            p = Packet(self.packets_sent, traffic_gen_default_size, self.id, -1, self.env.now)
            while(self.hold == None): # se tiver desativado
                yield self.env.timeout(foo_delay)
            self.hold.put(p) # adiciona a array que contem os Packets gerados
            self.packets_sent += 1
            yield self.env.timeout(foo_delay)

# abstract class
class Active_Node(object):
    def __init__(self, env, enabled, consumption_rate, start_time=0.0):
        self.env              = env
        self.enabled          = enabled # ativado/desativado :: bool
        self.consumption_rate = consumption_rate # power consumption :: double
        self.start_time       = start_time
        self.elapsed_time     = 0
        self.total_time       = 0.0
        self.an_action        = env.process(self.an_run())

    def start(self):
        self.start_time = self.env.now
        self.enabled = True

    def end(self):
        self.total_time += self.elapsed_time
        self.elapsed_time = 0
        self.enabled = False

    def consumption(self):
        return self.consumption_rate * (self.total_time + self.elapsed_time)

    def an_run(self):
        while(True):
            if(self.enabled):
                self.elapsed_time = self.env.now - self.start_time
            yield self.env.timeout(foo_delay) # necessario para nao entrar em loop infinito

class RRH(Active_Node):
    def __init__(self, env, id, consumption_rate, antennas, enabled=True):
        self.env = env
        self.id = id
        self.antennas = antennas
        Active_Node.__init__(self, env, enabled, consumption_rate, self.env.now)

    def start(self):
        self.start_time = self.env.now
        for ant in antennas:
            ant.start()
        self.enabled = True

    def end(self):
        for ant in antennas:
            ant.end()
        self.enabled = False

    def consumption(self):
        antennas_consumption = 0
        for ant in antennas:
            antennas_consumption += ant.consumption()
        return (self.consumption_rate * self.total_time) + antennas_consumption

    def __repr__(self):
        return "RRH - id: {}".\
            format(self.id)

class Cellsite(object):
    def __init__(self, env, id, rrh, users, consumption, onus):
        self.env            = env # environment do SimPy
        self.id             = id # identificador :: int
        self.rrh            = rrh # conjunto de RRH(s) :: RRH []
        self.onus           = onus # conjunto de ONU(s) :: ONU []
        self.users          = users # usuarios atendidos :: User []

    def calcTotalConsumption(self):
        total = 0
        for r in self.rrh:
            total += r.consumption()
        for o in self.onus:
            total += onus.consumption()
        return total

    def __repr__(self):
        return "Cellsite - id: {}, id_sender: {}, freq: {}, bandwidth: {}".\
            format(self.id, self.id_sender, self.freq, self.bandwidth)

class Antenna(Traffic_Generator, Active_Node):
    def __init__(self, env, id, target_up, consumption_rate, bitRate, distance, enabled=True, rate_dist=trafgen_def_dist):
        self.env            = env # environment
        self.id             = id # id da antena
        self.bitRate        = bitRate # taxa de transmissao
        self.target_up      = target_up # saida (possivelmente ONU)
        self.store          = simpy.Store(self.env)
        self.delay          = distance / float(Light_Speed) # delay upstream
        self.consumption_rate = consumption_rate
        Traffic_Generator.__init__(self, self.env, self.id, rate_dist, self.store)
        Active_Node.__init__(self, self.env, enabled, self.consumption_rate, self.env.now)
        self.action         = env.process(self.run()) # main loop

    def run(self):
        while(True):
            if(self.enabled):
                pkt = yield self.store.get() # espera algum dado ser gerado
                print(str(self), "picked", str(pkt), "at", self.env.now)
                if(self.target_up != None):
                    print(str(self), "delivering", str(pkt), "to", str(self.target_up), "at", self.env.now)
                    yield self.env.timeout(pkt.size / (self.bitRate / 8)) # delay de encaminhamento
                    yield self.env.timeout(self.delay) # delay de transmissao
                    print(str(self), "delivered at", self.env.now)
                    self.env.process(self.target_up.put(pkt, up=True)) # coloca na onu

                    self.end() # TEST!!
            yield self.env.timeout(foo_delay)

    def __repr__(self):
        return "Antenna - id: {}".\
            format(self.id)

# data
class Packet(object):
    def __init__(self, id, size, src, dst, init_time, freq=-1):
        self.id    = id
        self.size  = size # tamanho
        self.src   = src # origem
        self.dst   = dst # destino
        self.init_time = init_time
        self.waited_time = 0 # tempo de espera na fila
        self.freq = freq

    # def __repr__(self):
    #     return "Packet - id: {}, source: {}, destination: {}, init_time: {}, waited_time: {}, size: {}, freq: {}".\
    #         format(self.id, self.src, self.dst, self.init_time, self.waited_time, self.size, self.freq)

    def __repr__(self): # forma compacta
        return "Packet - id: {}, init_time: {}".\
            format(self.id, self.init_time)

# abstract class
class Virtual_Machine(object):
    def func(self, r):
        return r

class Foo_VM(Virtual_Machine):
    def __init__(self, env):
        self.env = env

    def func(self, o):
        print(str(self), "received", str(o), "at", self.env.now)
        yield self.env.timeout(foo_delay)
        print(str(self), "completed its function; returning object at", self.env.now)
        return o

    def __repr__(self):
        return "Foo VM - (n/a)"

# VDBA
class DBA_default(Active_Node, Virtual_Machine):
    def __init__(self, env, node, consumption_rate, delay=0, enabled=True):
        self.env = env

        self.res_vpons = simpy.Resource(self.env, capacity=1)
        self.vpons = []

        self.res_busy = simpy.Resource(self.env, capacity=1)
        self.busy = False
        self.busy_onu = -1 # onu que esta sendo gerado o grant; inicia em nenhuma

        self.res_requests = simpy.Resource(self.env, capacity=1)
        self.requests = []

        self.max_per_vpon = 6 # numero maximo de onus por vpon (?)
        self.freq_available = 0 # proxima frequencia disponivel
        self.node = node
        self.delay = delay # delay para execucao da funcao
        Active_Node.__init__(self, env, enabled, consumption_rate, self.env.now)

    def send_new_grant(self, r, vpon):
        # generate grant
        g = Grant(r.id_sender, vpon.free_time, r.bandwidth, vpon.freq)
        print(str(self), "generated", str(g), "at", self.env.now)
        # available time is incremented (in the VPON)
        vpon.free_time += self.node.time_to_onu(r)
        yield self.env.process(self.node.send_down(g))

    def assign_vpon(self, onu):
        new_vpon = None
        print(str(self), "will assign new vpon to ONU with id=" + str(onu), "at", self.env.now)
        # get next vpon with available onus
        with self.res_vpons.request() as req:
            yield req
            for v in self.vpons:
                if(len(v.onus) < self.max_per_vpon):
                    vpon = v
                    vpon.onus.append(onu)
                    break
            if(new_vpon == None):
                new_vpon = VPON([], self.freq_available, self.env.now)
                self.vpons.append(new_vpon)
                self.freq_available += 1
        return new_vpon

    def func(self, r):
        if(type(r) is Request):
            print(str(self), "is executing its function at", self.env.now)
            # if DBA is already busy with another onu, add request to store
            if(self.busy and r.id_sender != self.busy_onu):
                with self.res_requests.request() as req:
                    yield req
                    self.requests.append(r)
            # DBA is free
            else:
                vpon = None
                # delay to generate grant
                self.env.timeout(self.delay)
                # DBA is busy from now on
                with self.res_busy.request() as req:
                    yield req
                    self.busy = True
                    self.busy_onu = r.id_sender
                # find VPON by ONU ID
                with self.res_vpons.request() as req:
                    yield req
                    for v in self.vpons:
                        if(r.id_sender in v.onus):
                            vpon = v
                            break
                # none found -> assign a new
                if(vpon == None):
                    vpon = yield self.env.process(self.assign_vpon(r.id_sender))
                # generate and send grant
                self.env.process(self.send_new_grant(r, vpon))
                # DBA is free from now on
                with self.res_busy.request() as req:
                    yield req
                    self.busy = False
                    self.busy_onu = -1
                # if there is more request, call itself again
                with self.res_requests.request() as req:
                    yield req
                    if(len(self.requests) > 0):
                        self.env.process(self.func(self.requests.pop(0))) # archived requests
            return None
        else:
            return r

    def __repr__(self):
        return "DBA_default - (n/a)"

# DBA_default request
class Request(Packet):
    def __init__(self, id, id_sender, freq, bandwidth):
        self.id_sender      = id_sender
        self.freq           = freq
        self.bandwidth      = bandwidth
        Packet.__init__(self, id, 0, id_sender, -1, -1)

    def __repr__(self):
        return "Request - id: {}, id_sender: {}, freq: {}, bandwidth: {}".\
            format(self.id, self.id_sender, self.freq, self.bandwidth)

# DBA_default grant
class Grant(Packet):
    def __init__(self, onu, init_time, size, freq):
        self.onu = onu # onu alvo
        Packet.__init__(self, -1, size, -1, -1, init_time, freq=freq)

    def __repr__(self):
        return "Grant - onu: {}, init_time: {}, size: {}, freq: {},".\
            format(self.onu, self.init_time, self.size, self.freq)

# DBA_default VPON
class VPON(object):
    def __init__(self, onus, freq, now):
        self.onus = onus # onus conectadas
        self.freq = freq # frequencia
        self.free_time = now # tempo em que esta livre

    def __repr__(self):
        return "VPON - freq: {}, free_time: {}".\
            format(self.freq, self.free_time)

# Splitter passivo; demultiplexador
class Splitter(object):
    def __init__(self, env, id, target_up, target_down, distance_up):
        self.env            = env
        self.id             = id
        self.target_up      = target_up # alvo em upstreaming
        self.target_down    = target_down # alvos em downstreaming
        if(target_down != None):
            sorted(self.target_down, key=lambda target: target.delay_up) # organiza pelo tempo de upstreaming dos peers
        self.delay_up       = distance_up / float(Light_Speed) # tempo para transmitir upstream

    def put(self, pkt, down=False, up=False):
        print(str(self), "receveid pkt", str(pkt), "at", self.env.now)
        if(down and len(self.target_down) > 0):
            counted = 0
            for t in self.target_down:
                yield self.env.timeout(t.delay_up - counted)
                counted = t.delay_up
                self.env.process(t.put(pkt, down=True))
        if(up and self.target_up != None):
            yield self.env.timeout(self.delay_up)
            print(str(self), "finished sending pkt", str(pkt), "at", self.env.now)
            self.env.process(self.target_up.put(pkt, up=True))

    def __repr__(self):
        return "Splitter - (n/a)"

class Processing_Node(Active_Node):
    def __init__(self, env, id, consumption_rate, target_up, target_down, bitRate_up, bitRate_down, distance, enabled=True, DU=[], LC=[]):
        self.env            = env
        self.id             = id
        self.DU             = DU  # digital units :: Digital_Unit []
        self.LC             = LC
        self.bitRate_up     = bitRate_up
        self.bitRate_down   = bitRate_down
        self.res_hold_up	= simpy.Resource(self.env, capacity=1) # semaforo de dados upstream
        self.res_hold_down	= simpy.Resource(self.env, capacity=1) # semaforo de dados downstream
        self.hold_up        = [] # array de dados upstream
        self.hold_down      = [] # array de dados downstream
        self.target_up      = target_up # target downstreaming
        self.target_down    = target_down   # target upstreaming
        self.delay_up       = distance / float(Light_Speed)
        Active_Node.__init__(self, env, enabled, consumption_rate, self.env.now)
        self.action         = self.env.process(self.run())

    def time_to_onu(self, r, target=None):
        if(target == None):
            target = self.target_down
        if(type(target) is Splitter):
            for t in target.target_down:
                delay_acc = self.time_to_onu(r, target=t)
                if(delay_acc > 0):
                    return delay_total + target.delay_up
        elif(type(target) is ONU):
            if(target.id == r.id_sender):
                return target.delay_up + (r.bandwidth / (target.bitRate_up / 8))
        else:
            delay_acc = self.time_to_onu(id, target=target.target_down)
            if(delay_acc > 0):
                return delay_acc + target.delay_up
        return 0

    def start(self):
        self.start_time = self.env.now
        for d in DU:
            d.start()
        for l in LC:
            l.start()
        self.enabled = True

    def end(self):
        for d in DU:
            d.end()
        for l in LC:
            l.end()
        self.enabled = False

    def consumption(self):
        total = 0
        for d in DU:
            total += d.consumption()
        for l in LC:
            total += l.consumption()
        return (self.consumption_rate * self.total_time) + total

    # upstreaming
    def send_up(self, o):
        if(self.target_up != None):
            yield self.env.timeout(o.size / (self.bitRate_up / 8)) # transmission
            yield self.env.timeout(self.delay_up) # propagation
            print(str(self), "finished sending (upstream) pkt at", self.env.now)
            self.env.process(self.target_up.put(o, up=True))

    # downstreaming
    def send_down(self, o):
        if(self.target_down != None):
            yield self.env.timeout(o.size / (self.bitRate_down / 8)) # transmission
            yield self.env.timeout(self.target_down.delay_up) # propagation
            print(str(self), "finished sending (downstream) pkt at", self.env.now)
            self.env.process(self.target_down.put(o, down=True))

    def put(self, pkt, down=False, up=False):
        print(str(self), "receveid pkt", str(pkt), "at", self.env.now)
        if(self.enabled):
            if(down):
                with self.res_hold_down.request() as req:
                    yield req
                    self.hold_down.append(pkt)
            if(up):
                with self.res_hold_up.request() as req:
                    yield req
                    self.hold_up.append(pkt)
        else:
            if(down):
                self.env.process(self.send_down(pkt))
            if(up):
                self.env.process(self.send_up(pkt))

    def run(self):
        while(True):
            if(self.enabled):
                if(len(self.hold_up) > 0):
                    with self.res_hold_down.request() as req:
                        yield req
                        o = self.hold_up.pop(0)
                        print(str(self), "is sending", str(o),"to LCs at", self.env.now)
                        target_lc = None
                        if(len(self.LC) > 0):
                            for l in self.LC:
                                if(o.freq == l.freq):
                                    target_lc = l
                                    break
                            if(target_lc != None):
                                self.env.process(target_lc.put(o))

                if(len(self.hold_down) > 0):
                    with self.res_hold_down.request() as req:
                        yield req
                        print(str(self), "is going to send (downstream) at", self.env.now)
                        self.env.process(self.send_down(self.hold_down.pop(0)))
            yield self.env.timeout(foo_delay)

    def __repr__(self):
        return "Processing Node - id: {}".\
            format(self.id)

class Digital_Unit(Active_Node):
    def __init__(self, env, id, consumption_rate, node, out, vms=None, enabled=True):
        self.id = id
        self.env = env
        self.node = node
        self.res_vms = simpy.Resource(self.env, capacity=1)
        self.vms = vms
        self.out = out
        Active_Node.__init__(self, env, enabled, consumption_rate, self.env.now)

    def config(node, DU, config): # configure exit ports; singleton function
        for tp in config:
            d1 = None
            d2 = None
            for d in DU:
                if(d.id == tp[0]):
                    d1 = d
                if(d.id == tp[1]):
                    d2 = d
            if(d1 == None or d2 == None): # config failed
                break
            d1.out = d

    def append_vm(self, vm): # append vms
        with self.res_vms.request() as req:
            yield req
            self.vms.append(vm)

    def execute_functions(self, o):
        print(str(self), "will execute functions at", self.env.now)
        yield self.env.timeout(0)
        if(self.vms == None):
            self.env.process(self.out.send_up(o))
        else:
            for v in self.vms:
                print(str(self), "is using VM", str(v), "on", str(o), "at", self.env.now)
                o = yield self.env.process(v.func(o))
                if(o == None):
                    return
            print(str(self), "is sending the left data to", str(self.out), "at", self.env.now)

            if(type(self.out) is Digital_Unit):
                self.env.process(self.out.execute_functions(o))
            elif(type(self.out) is Processing_Node):
                self.env.process(self.out.send_up(o))

    def __repr__(self):
        return "Digital Unit - (n/a)"

class LineCard(Active_Node):
    def __init__(self, env, freq, delay=0, out=None, enabled=True, consumption=0):
        self.env = env
        self.delay = delay
        self.freq = freq
        self.out = out
        Active_Node.__init__(self, env, enabled, consumption, self.env.now)

    def put(self, p):
        if(self.out != None and self.enabled == True):
            print(str(self), "is pushing", p, "to a DU at", self.env.now)
            yield self.env.timeout(self.delay)
            self.env.process(self.out.execute_functions(p))

    def __repr__(self):
        return "LineCard - freq: {}".\
            format(self.freq)

class ONU(Active_Node):
    def __init__(self, env, id, target_up, target_down, consumption, cellsite, bitRate_up, bitRate_down, distance, enabled=True, freq=-1, threshold=0):
        self.env            = env
        self.id             = id
        self.freq           = freq
        self.consumption    = consumption # power consumption
        self.target_up      = target_up
        self.target_down    = target_down
        self.cellsite       = cellsite # id cellsite
        self.delay_up       = distance / float(Light_Speed)

        self.total_hold_size = 0

        # semaforos
        self.res_hold_up	= simpy.Resource(self.env, capacity=1) # semaforo de dados upstream
        self.res_hold_down	= simpy.Resource(self.env, capacity=1) # semaforo de dados downstream
        self.res_grants		= simpy.Resource(self.env, capacity=1) # semaforo de grants recebidos
        self.res_requests	= simpy.Resource(self.env, capacity=1) # semaforo de requests gerados

        self.hold_up        = [] # array de dados upstream
        self.hold_down      = [] # array de dados downstream
        self.grants         = [] # array de grants recebidos
        self.requests       = [] # array de requests gerados para serem enviados

        self.request_counting = 0
        self.bitRate_up     = bitRate_up
        self.bitRate_down   = bitRate_down
        self.threshold      = threshold

        Active_Node.__init__(self, env, enabled, consumption, self.env.now)
        self.action         = env.process(self.run()) # loop

    # receive new data to upstream/downstream it
    def put(self, pkt, down=False, up=False):
        print(str(self), "receveid pkt", str(pkt), "at", self.env.now)
        if(self.enabled):
            if(down):
                # one grant
                if(type(pkt) is Grant and pkt.onu == self.id):
                    with self.res_grants.request() as req:
                        yield req
                        self.grants.append([pkt])
                # many grants
                if(type(pkt) is list and pkt[0].onu == self.id_sender):
                    with self.res_grants.request() as req:
                        yield req
                        self.grants.append(pkt)
                # packet
                elif(type(pkt) is Packet):
                    with self.res_hold_down.request() as req:
                        yield req
                        self.hold_down.append(pkt)

            if(up):
                with self.res_hold_up.request() as req:
                    yield req
                    self.hold_up.append(pkt)
                    self.total_hold_size += pkt.size
                    if(self.total_hold_size > self.threshold):
                        self.env.process(self.gen_request())

    # generate a request
    def gen_request(self):
        print(str(self), "is generating a request at", self.env.now)
        with self.res_requests.request() as req:
            yield req
            self.requests.append(Request(self.request_counting, self.id, -1, self.total_hold_size))
            self.request_counting += 1

    # upstreaming
    def send_up(self, o):
        if(self.target_up != None):
            yield self.env.timeout(o.size / (self.bitRate_up / 8)) # transmission
            yield self.env.timeout(self.delay_up) # propagation
            print(str(self), "finished sending (upstream) pkt at", self.env.now)
            self.env.process(self.target_up.put(o, up=True))

    # downstreaming
    def send_down(self, o):
        if(self.target_down != None):
            yield self.env.timeout(o.size / (self.bitRate_down / 8)) # transmission
            yield self.env.timeout(self.target_down.delay_up) # propagation
            print(str(self), "finished sending (downstream) pkt at", self.env.now)
            self.env.process(self.target_down.put(o, down=True))

    # use the grant(s) you received
    def use_grant(self, grants):
        sorted(grants, key=lambda grant: grant.init_time) # organiza do menor pro maior
        data_to_transfer = []
        for g in grants:
            # yield self.env.timeout(g.init_time - self.env.now)
            to_wait = g.init_time - self.env.now
            if(to_wait < 0):
                to_wait = 0
            print(str(self), "is going to wait", str(to_wait), "at", self.env.now)
            yield self.env.timeout(to_wait)
            with self.res_hold_up.request() as req:
                yield req
                total = 0
                while(len(self.hold_up) > 0):
                    p = self.hold_up.pop(0)
                    if(total + p.size > g.size):
                        self.hold_up.insert(0, p)
                        break
                    data_to_transfer.append(p)
                    total += p.size
            print(str(self), "is going to send (upstream) all data permited through grant at", self.env.now)
            for d in data_to_transfer: # (self, id, size, src, dst, init_time):
                d.src = self.id
                d.waited_time = self.env.now - d.init_time
                d.freq = g.freq
                yield self.env.process(self.send_up(d))

    def run(self):
        while True:
            if(self.enabled):
                if(len(self.requests) > 0): # if you have requests to send
                    with self.res_requests.request() as req:
                        yield req
                        print(str(self), "is sending a request at", self.env.now)
                        self.env.process(self.send_up(self.requests.pop(0)))

                if(len(self.grants) > 0): # if you got grants
                    with self.res_grants.request() as req:
                        yield req
                        print(str(self), "is going to use a grant at", self.env.now)
                        self.env.process(self.use_grant(self.grants.pop(0)))
                if(len(self.hold_down) > 0): # if you got downstreaming data
                    with self.res_hold_down as req:
                        yield req
                        print(str(self), "is going to send (downstream) at", self.env.now)
                        self.env.process(self.send_down(self.hold_down.pop(0)))

            yield self.env.timeout(foo_delay)

    def __repr__(self):
        return "ONU - id: {}".\
            format(self.id)
