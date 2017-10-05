import simpy
import functools
import random
import time

# Default attributes

# default traffic generator size:
tg_default_size = lambda x: 50
# default traffic generator distribution:
tg_default_dist = lambda x: random.expovariate(10)
# default DBA bandwidth:
DBA_IPACT_default_bandwidth = 1250000 # 1.25 Gb/s, bandwidth for each frequency/vpon
# default ONU consumption:
ONU_consumption = lambda x: 0
# default Processing Node consumption:
PN_consumption = lambda x: 0
# default LineCard consumption:
LC_consumption = lambda x: 0
# default Digital Unit consumption:
DU_consumption = lambda x: 0
# default ONU threshold:
ONU_threshold = 0
# default ONU bit rate downstreaming:
ONU_bitRate_down = 0
# default ONU bit rate upstreaming:
ONU_bitRate_up = 0
# default Processing Node downstreaming:
PN_bitRate_down = 0
# default Processing Node upstreaming:
PN_bitRate_up = 0

# Constants

# Light Speed:
Light_Speed = 300000000
# Radio Speed:
Antenna_Speed = 300000000
# interactions delay (to not overload the simulation):
foo_delay = 0.0001 # arbitrary

# statistics class
class Writer(object):
    def __init__(self, suffix, start="#\n", date=True):
        filename = ""
        if(date):
            filename = time.strftime(suffix + "%d%m%Y_%H%M%S_output.dat")
        else:
            filename = suffix + "output.dat"
        self.file = open(filename, 'w')
        print("Opening file", filename, "to write")
        self.write(start)

    def write(self, text):
        self.file.write(text)

    def close(self):
        self.file.close()

# packet_w = Writer("packet_", start="# id src init_time waited_time freq processed_time\n")
packet_w = None

# topology functions
def create_topology(env, qnty_ant, qnty_onu, qnty_pn, qnty_splt, matrix, max_frequency):
    id_onu = 0
    id_pn = 0
    id_ant = 0
    nodes = []

    # create nodes
    for i in range(qnty_ant):
        print("Creating Antenna #", id_ant)
        nodes.append(Antenna(env, id_ant, None, 0, 0, 0))
        id_ant += 1

    for i in range(qnty_onu):
        print("Creating ONU #", id_onu)
        nodes.append(ONU(env, id_onu, None, None, ONU_consumption, None, ONU_bitRate_up, ONU_bitRate_down, 0, threshold=ONU_threshold))
        id_onu += 1

    for i in range(qnty_pn):
        print("Creating Processing Node #", id_pn)
        # create lcs and put them to sleep
        pn_lcs = []
        pn_lcs.append(LineCard(env, -1, consumption=LC_consumption)) # control's LC; perhaps with 0 consumption and enabled
        for j in range(max_frequency):
            pn_lcs.append(LineCard(env, j, consumption=LC_consumption))
        # create DUs
        pn_dus = []
        # attach LCs and DUs
        pn_node = Processing_Node(env, id_pn, None, None, PN_consumption, PN_bitRate_up, PN_bitRate_down, 0, LC=pn_lcs, DU=pn_dus)

        # add a Digital Unit with DBA
        # def __init__(self, env, node, consumption_rate, min_band, max_frequency, enabled=True, delay=0):
        pn_node.append_DU(DU_consumption, pn_node, -1, enabled=True, vms=[DBA_Assigner(env, pn_node, 0, max_frequency)])

        # add a Digital Unit to BB processing (not real BB processing)
        pn_node.append_DU(DU_consumption, pn_node, 0, enabled=True, vms=[Foo_BB_VM(env)])

        nodes.append(pn_node)
        id_pn += 1

    for i in range(qnty_splt):
        print("Creating Splitter")
        nodes.append(Splitter(env, 0, None, None, 0))

    print("Total nodes:", len(nodes))

    # connect nodes
    for m in matrix:
        n_one = nodes[m[0]]
        n_two = nodes[m[1]]
        dist = m[2]
        print("Attaching", str(n_one), "to", str(n_two), "with a distance of", str(dist))
        n_one.target_up = n_two
        if(type(n_two) is ONU or type(n_two) is Splitter):
            n_two.target_down.append(n_one)
        else:
            n_two.target_down = n_one
        if(type(n_one) is Antenna):
            n_one.delay = dist / float(Antenna_Speed)
        else:
            n_one.delay_up = dist / float(Light_Speed)

    def set_local_nodes(node):
        if(isinstance(node, Splitter)):
            arr = []
            for t in node.target_down:
                arr += set_local_nodes(t)
            return arr
        elif(isinstance(node, Processing_Node)):
            print(str(node), "is a local node")
            return [node]
        else:
            return []

    # set local nodes
    for n in nodes:
        if(isinstance(n, Processing_Node)):
            print("Setting local nodes to", str(n), "...")
            n.local_nodes = set_local_nodes(n.target_down)

    return nodes

def create_topology_from_nodes(env, matrix, nodes):
    for m in matrix:
        n_one = nodes[m[0]]
        n_two = nodes[m[1]]
        dist = m[2]
        print("Attaching", str(n_one), "to", str(n_two), "with a distance of", str(dist))
        n_one.target_up = n_two
        if(type(n_two) is ONU or type(n_two) is Splitter):
            n_two.target_down.append(n_one)
        else:
            n_two.target_down = n_one
        if(type(n_one) is Antenna):
            n_one.delay = dist / float(Antenna_Speed)
        else:
            n_one.delay_up = dist / float(Light_Speed)

    # remove all DBAs/VPONs
    for n in nodes:
        if(type(n) is Processing_Node):
            for i in range(len(n.DU)):
                if(type(n.DU[i]) is DBA_IPACT):
                    print("Removing DBA IPACT from a DU")
                    n.DU.remove(n.DU[i])
                    i = i - 1

    return nodes

# abstract class
class Traffic_Generator(object):
    def __init__(self, env, id, distribution, size, hold=None):
        self.env              = env
        self.id               = id
        self.dist             = distribution # callable
        self.size             = size # callable
        self.hold             = hold # armazena os Packets
        self.trafic_action    = env.process(self.trafic_run())
        self.packets_sent     = 0

    def trafic_run(self):
        while True:
            yield self.env.timeout(self.dist(self)) # tempo de espera
            p = Packet(self.packets_sent, self.size(self), self.id, -1, self.env.now)
            while(self.hold == None): # se tiver desativado
                yield self.env.timeout(foo_delay)
            self.hold.put(p) # adiciona a array que contem os Packets gerados
            self.packets_sent += 1
            # yield self.env.timeout(foo_delay)

# abstract class
class Active_Node(object):
    def __init__(self, env, enabled, consumption_rate, objs, start_time):
        self.env              = env
        self.enabled          = enabled # ativado/desativado :: bool
        self.consumption_rate = consumption_rate # power consumption :: double
        self.start_time       = start_time
        self.elapsed_time     = 0
        self.total_time       = 0.0
        self.an_action        = env.process(self.an_run())
        self.obj_sleeping     = [] # sleeping objects
        self.objs             = objs # active nodes inside this active node

    def start(self):
        self.start_time = self.env.now
        self.enabled = True
        for o in self.obj_sleeping:
            o.start()
        self.obj_sleeping = []

    def end(self):
        self.total_time += self.elapsed_time
        self.elapsed_time = 0
        self.enabled = False
        for o in self.objs:
            if(o.enabled is True):
                self.obj_sleeping.append(o)
                o.end()

    def consumption(self):
        total = 0
        for o in self.objs:
            total += o.consumption
        return total + self.consumption_rate(self) * (self.total_time + self.elapsed_time)

    def an_run(self):
        while(True):
            if(self.enabled):
                self.elapsed_time = self.env.now - self.start_time
            yield self.env.timeout(foo_delay) # necessario para nao entrar em loop infinito

# unused
class RRH(Active_Node):
    def __init__(self, env, id, consumption_rate, antennas, enabled=True):
        self.env = env
        self.id = id
        self.antennas = antennas
        Active_Node.__init__(self, env, enabled, consumption_rate, antennas,self.env.now)

    def __repr__(self):
        return "RRH - id: {}".\
            format(self.id)

# unused
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

# traffic gen implemented
class Antenna(Traffic_Generator, Active_Node):
    def __init__(self, env, id, target_up, consumption_rate, bitRate, distance, enabled=True):
        self.env            = env # environment
        self.id             = id # id da antena
        self.bitRate        = bitRate # taxa de transmissao
        self.target_up      = target_up # saida (possivelmente ONU)
        self.store          = simpy.Store(self.env)
        self.delay          = distance / float(Antenna_Speed) # delay upstream
        self.consumption_rate = consumption_rate
        Traffic_Generator.__init__(self, self.env, self.id, tg_default_dist, tg_default_size, hold=self.store)
        Active_Node.__init__(self, self.env, enabled, self.consumption_rate, [], self.env.now)
        self.action         = env.process(self.run()) # main loop

    def start(self):
        self.start_time = self.env.now
        self.enabled = True
        self.store = simpy.Store(self.env)

    def end(self):
        self.total_time += self.elapsed_time
        self.elapsed_time = 0
        self.enabled = False
        self.store = None

    def run(self):
        while(True):
            if(self.enabled):
                pkt = yield self.store.get() # espera algum dado ser gerado
                print(str(self), "picked", str(pkt), "at", self.env.now)
                if(self.target_up != None):
                    print(str(self), "delivering", str(pkt), "to", str(self.target_up), "at", self.env.now)
                    if(self.bitRate > 0):
                        yield self.env.timeout(pkt.size / (self.bitRate / 8)) # delay de encaminhamento
                    yield self.env.timeout(self.delay) # delay de transmissao
                    print(str(self), "delivered at", self.env.now)
                    self.env.process(self.target_up.put(pkt, up=True)) # coloca na onu
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

    def __repr__(self): # forma compacta
        return "Packet - id: {}, src: {}, init_time: {}".\
            format(self.id, self.src, self.init_time)

# abstract class
class Virtual_Machine(object):
    def func(self, r):
        return r

# test VM
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

# test VM (writing test)
class Foo_BB_VM(Virtual_Machine):
    def __init__(self, env):
        self.env = env

    def func(self, o):
        if(packet_w != None):
            if(type(o) is Packet):
                packet_w.write("{} {} {} {} {} {}\n".format(o.id, o.src, o.init_time, o.waited_time, o.freq, self.env.now))
            if(type(o) is list and type(o[0]) is Packet):
                for p in o:
                    packet_w.write("{} {} {} {} {} {}\n".format(p.id, p.src, p.init_time, p.waited_time, p.freq, self.env.now))
            yield self.env.timeout(0)
        return None

    def __repr__(self):
        return "Foo BB VM - (n/a)"

# DBA_default request
class Request(Packet):
    def __init__(self, id, id_sender, freq, bandwidth, ack):
        self.id_sender      = id_sender
        self.freq           = freq
        self.bandwidth      = bandwidth
        self.ack            = ack
        Packet.__init__(self, id, 0, id_sender, -1, -1)

    def __repr__(self):
        return "Request - id: {}, id_sender: {}, freq: {}, bandwidth: {}, ack: {}".\
            format(self.id, self.id_sender, self.freq, self.bandwidth, self.ack)

# DBA_default grant
class Grant(Packet):
    def __init__(self, onu, init_time, size, freq, ack):
        self.onu = onu # onu alvo
        self.ack = ack
        Packet.__init__(self, -1, size, -1, -1, init_time, freq=freq)

    def __repr__(self):
        return "Grant - onu: {}, init_time: {}, size: {}, freq: {}, ack: {}".\
            format(self.onu, self.init_time, self.size, self.freq, self.ack)

# Splitter passivo; demultiplexador
class Splitter(object):
    def __init__(self, env, id, target_up, target_down, distance_up):
        self.env            = env
        self.id             = id
        self.target_up      = target_up # alvo em upstreaming
        self.target_down    = target_down # alvos em downstreaming
        self.target_down = []
        self.delay_up       = distance_up / float(Light_Speed) # tempo para transmitir upstream

    def put(self, pkt, down=False, up=False):
        print(str(self), "receveid pkt", str(pkt), "at", self.env.now)
        if(down and len(self.target_down) > 0):
            if(self.target_down != None):
                self.target_down.sort(key=lambda target: target.delay_up) # organiza pelo tempo de upstreaming dos peers
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

# OLT or local node (fog)
class Processing_Node(Active_Node):
    def __init__(self, env, id, target_up, target_down, consumption_rate, bitRate_up, bitRate_down, distance, enabled=True, DU=[], LC=[]):
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
        Active_Node.__init__(self, env, enabled, consumption_rate, DU + LC, self.env.now)
        self.action         = self.env.process(self.run())

    # calculate time required transfer size bytes to certain onu from this node
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

    # calculate time required transfer size bytes from certain onu to this node
    def time_from_onu(self, size, id_onu, target=None):
        if(target == None):
            target = self
        if(type(target) is Splitter):
            for t in target.target_down:
                delay_acc = self.time_to_onu(size, id_onu, target=t)
                if(delay_acc > 0):
                    return delay_acc + target.delay_up
        elif(type(target) is ONU):
            if(target.id == id_onu):
                if(target.bitRate_up > 0):
                    return target.delay_up + (size / (target.bitRate_up / 8))
                else:
                    return target.delay_up
        else:
            delay_acc = self.time_to_onu(size, id_onu, target=target.target_down)
            if(delay_acc > 0):
                if(target.bitRate_up > 0 and self != target):
                    delay_acc += (size / (target.bitRate_up / 8)) + target.delay_up
                return delay_acc
        return 0

    def append_DU(self, consumption, out, freq, enabled=False, vms=None):
        # def __init__(self, env, id, consumption_rate, node, out, vms=None, enabled=False)
        # nodes[8].append_DU(20, nodes[8], -1, enabled=True)
        du = Digital_Unit(self.env, len(self.DU), consumption, self, out, vms=vms, enabled=enabled)
        lc = self.LC[freq+1]
        if(lc.enabled == False):
            lc.start()
        lc.out = du
        self.DU.append(du)
        print(str(self), "is creating a Digital_Unit and attaching to", lc)

    # upstreaming
    def send_up(self, o):
        if(self.target_up != None):
            if(self.bitRate_up > 0):
                yield self.env.timeout(o.size / (self.bitRate_up / 8)) # transmission
            yield self.env.timeout(self.delay_up) # propagation
            print(str(self), "finished sending (upstream) pkt at", self.env.now)
            self.env.process(self.target_up.put(o, up=True))

    # downstreaming
    def send_down(self, o):
        if(self.target_down != None):
            if(self.bitRate_down > 0):
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
            print(str(self), "is not enabled at", self.env.now)
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
                                true_object = o
                                if(type(o) is list):
                                    true_object = o[0]
                                if(true_object.freq == l.freq):
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
 
# chain of virtualized functions
class Digital_Unit(Active_Node):
    def __init__(self, env, id, consumption_rate, node, out, vms=None, enabled=False):
        self.id = id
        self.env = env
        self.node = node
        self.res_vms = simpy.Resource(self.env, capacity=1)
        self.vms = vms
        self.out = out
        Active_Node.__init__(self, env, enabled, consumption_rate, vms, self.env.now)

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
        print(str(self), "is appending VM", vm)
        with self.res_vms.request() as req:
            yield req
            self.vms.append(vm)

    def execute_functions(self, o):
        print(str(self), "will execute functions at", self.env.now)
        yield self.env.timeout(0)
        if(self.vms == None):
            self.env.process(self.out.send_up(o))
        else:
            # i = 0
            # while(i < len(self.vms)):
            #     print(str(self), "is using VM", str(self.vms[i]), "on", str(o), "at", self.env.now)
            #     o = yield self.env.process(self.vms[i].func(o))
            #     print(str(self), "returned", str(o), "at", self.env.now)
            #     if(o == None):
            #         return
            #     i += 1
            for v in self.vms:
                print(str(self), "is using VM", str(v), "on", str(o), "at", self.env.now)
                o = yield self.env.process(v.func(o))
                print(str(self), "returned", str(o), "from execute functions at", self.env.now)
                if(o == None):
                    return
            print(str(self), "is sending the left data to", str(self.out), "at", self.env.now)

            if(type(self.out) is Digital_Unit):
                self.env.process(self.out.execute_functions(o))
            elif(type(self.out) is Processing_Node):
                self.env.process(self.out.send_up(o))

    def __repr__(self):
        return "Digital Unit - (n/a)"

# linecard attuned to a frequency
class LineCard(Active_Node):
    def __init__(self, env, freq, delay=0, out=None, enabled=False, consumption=0):
        self.env = env
        self.delay = delay
        self.freq = freq
        self.out = out
        Active_Node.__init__(self, env, enabled, consumption, [], self.env.now)

    def put(self, p):
        if(self.out != None and self.enabled == True):
            print(str(self), "is pushing", p, "to a DU at", self.env.now)
            yield self.env.timeout(self.delay)
            self.env.process(self.out.execute_functions(p))

    def __repr__(self):
        return "LineCard - freq: {}".\
            format(self.freq)

# ONU
class ONU(Active_Node):
    def __init__(self, env, id, target_up, target_down, consumption, cellsite, bitRate_up, bitRate_down, distance, enabled=True, freq=-1, threshold=0):
        self.env            = env
        self.id             = id
        self.freq           = freq
        self.consumption    = consumption # power consumption
        self.target_up      = target_up
        if(target_down == None):
            self.target_down = []
        else:
            self.target_down    = target_down
        self.cellsite       = cellsite # id cellsite
        self.delay_up       = distance / float(Light_Speed)

        self.total_hold_size = 0
        self.ack = 0

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

        Active_Node.__init__(self, env, enabled, consumption, [], self.env.now)
        self.action         = env.process(self.run()) # loop

    def end(self):
        self.total_time += self.elapsed_time
        self.elapsed_time = 0
        self.enabled = False
        with self.res_hold_up.request() as req1:
            yield req1
            with self.res_hold_down.request() as req2:
                yield req2
                with self.res_grants.request() as req3:
                    yield req3
                    with self.res_requests.request() as req4:
                        yield req4
                        self.hold_up        = []
                        self.hold_down      = []
                        self.grants         = []
                        self.requests       = []

    # receive new data to upstream/downstream it
    def put(self, pkt, down=False, up=False):
        print(str(self), "receveid pkt", str(pkt), "at", self.env.now)
        if(self.enabled):
            if(down):
                # one grant
                if(type(pkt) is Grant and pkt.onu == self.id):
                    with self.res_grants.request() as req:
                        yield req
                        self.grants.append(pkt)
                # many grants
                if(type(pkt) is list and type(pkt[0]) is Grant and pkt[0].onu == self.id_sender):
                    with self.res_grants.request() as req:
                        yield req
                        for g in pkt:
                            self.grants.append(g)
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
            self.requests.append(Request(self.request_counting, self.id, -1, self.total_hold_size, self.ack))
            self.request_counting += 1

    # upstreaming
    def send_up(self, o):
        if(self.target_up != None):
            if(self.bitRate_up > 0):
                yield self.env.timeout(o.size / (self.bitRate_up / 8)) # transmission
            yield self.env.timeout(self.delay_up) # propagation
            print(str(self), "finished sending (upstream) pkt at", self.env.now)
            self.env.process(self.target_up.put(o, up=True))

    # downstreaming
    def send_down(self, o):
        if(self.target_down != None):
            sorted(self.target_down, key=lambda target: target.delay_up)
            counted = 0
            for t in self.target_down:
                if(bitRate_down > 0):
                    additional_time = o.size / (self.bitRate_down / 8)
                else:
                    additional_time = 0
                yield self.env.timeout(additional_time + t.delay_up - counted) # errado?
                counted = additional_time + t.delay_up
                print(str(self), "finished sending (downstream) pkt at", self.env.now)
                self.env.process(t.put(o, down=True))
             # transmission
            yield self.env.timeout(self.target_down.delay_up) # propagation
            self.env.process(self.target_down.put(o, down=True))

    # use the grant(s) you received
    def use_grant(self, grant):
        data_to_transfer = []
        if(self.ack < grant.ack):
            self.ack = grant.ack
        to_wait = grant.init_time - self.env.now
        if(to_wait < 0):
        	print(str(self), "is going to discard grant, reason: negative wait time; at", self.env.now)
        print(str(self), "is going to wait", str(to_wait), "at", self.env.now)
        with self.res_hold_up.request() as req:
            yield req
            total = 0
            while(len(self.hold_up) > 0):
                p = self.hold_up.pop(0)
                if(total + p.size > grant.size):
                    self.hold_up.insert(0, p) # volta
                    break
                data_to_transfer.append(p)
                total += p.size
        print(str(self), "is going to send (upstream) all data permited through grant at", self.env.now)
        for d in data_to_transfer: # (self, id, size, src, dst, init_time):
            d.src = self.id
            d.waited_time = self.env.now - d.init_time
            d.freq = grant.freq

        yield self.env.timeout(to_wait)
        yield self.env.process(self.send_up(data_to_transfer))

    # action
    def run(self):
        while True:
            if(self.enabled):
                if(len(self.requests) > 0): # if you have requests to send
                    with self.res_requests.request() as req:
                        yield req
                        print(str(self), "is sending a request at", self.env.now)
                        self.env.process(self.send_up(self.requests.pop(0)))

                if(len(self.grants) > 0 and len(self.hold_up) > 0): # if you got grants
                    with self.res_grants.request() as req:
                        yield req
                        print(str(self), "is going to use a grant at", self.env.now)
                        sorted(self.grants, key=lambda grant: grant.init_time) # organiza do menor pro maior
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

# VDBA IPACT
class DBA_IPACT(Active_Node, Virtual_Machine):
    def __init__(self, env, node, consumption_rate, freq, bandwidth, delay=0, enabled=True):
        self.env = env
        self.node = node
        self.delay = delay # delay to execute
        self.freq = freq
        self.bandwidth = bandwidth

        self.busy = simpy.Resource(self.env, capacity=1)
        self.onus = [] # "connected" onus
        self.acks = {}
        self.bandwidth_used = 0
        self.removable_bandwidth = []
        self.free_time = self.env.now
        Active_Node.__init__(self, env, enabled, consumption_rate, [], self.env.now)

        self.action = self.env.process(self.run())

    # override function
    def end(self):
        self.total_time += self.elapsed_time
        self.elapsed_time = 0
        self.enabled = False
        self.onus = []
        self.acks = {}

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
                print("Receiving", str(r), "at", str(self.env.now))
                if(r.ack != self.acks[r.id_sender]): # not aligned acks!
                    print(str(self), "received duplicated request at", str(self.env.now))
                    return None
                # aligned acks
                time_to = self.node.time_to_onu(0, r.id_sender)
                time_from = self.node.time_from_onu(r.bandwidth, r.id_sender)

                if(self.bandwidth_used + r.bandwidth <= self.bandwidth):
                    # there is bandwidth!!
                    g = None
                    if(self.env.now + time_to > self.free_time):
                        g = Grant(r.id_sender, self.env.now + time_to + foo_delay, r.bandwidth, self.freq, self.acks[r.id_sender])
                        print(str(self), "generated", str(g), "at", self.env.now)
                        self.free_time = self.env.now + time_to + foo_delay + time_from
                    else:
                        g = Grant(r.id_sender, self.free_time + foo_delay, r.bandwidth, self.freq, self.acks[r.id_sender])
                        print(str(self), "generated", str(g), "at", self.env.now)
                        self.free_time = self.free_time + foo_delay + time_from

                    yield self.env.process(self.node.send_down(g))
                    self.bandwidth_used += r.bandwidth
                    # case there was more than 1 request in short time
                    removable = None
                    for f in self.removable_bandwidth:
                        if(f[2] == r.id_sender):
                            print(str(self), "Found duplicated id_sender on removable bandwidth, removing at", self.env.now)
                            removable = f
                            self.removable_bandwidth.remove(f)
                            break
                    # self.removable_bandwidth += [(self.free_time, r.bandwidth, r.id_sender)]
                    self.removable_bandwidth += [(self.env.now + 1 - foo_delay, r.bandwidth, r.id_sender)] # rodrigo!
                    print("Bandwidth available:", self.bandwidth - self.bandwidth_used, "at", self.env.now)
                    yield self.env.timeout(self.delay)
                    return None # return none

                else:
                    # no bandwidth
                    print(str(self), "has no bandwidth at", self.env.now)
                    if(len(self.node.local_nodes) > 0):
                        # activate more-local PN
                        print(str(self), "is activating a more local node at", self.env.now)
                        node = self.node.local_nodes.pop()
                        node.start()
                    else:
                        # no more local nodes!
                        pass
            else:
                # pass along to another dba
                print(str(self),"is passing along object", str(r), "at", str(self.env.now))
                return r

    def run(self):
        while(True):
            if(self.enabled and len(self.removable_bandwidth) > 0):
                z = self.removable_bandwidth.pop(0)
                if(z[0] > self.env.now):
                    yield self.env.timeout(z[0] - self.env.now)
                print("Removing ONU", z[2], "from DBA", str(self), "duo expired time at", self.env.now)
                self.bandwidth_used -= z[1]
                self.desassociate_onu(z[2])
                print("Bandwidth available:", self.bandwidth - self.bandwidth_used, "at", self.env.now)
            yield self.env.timeout(foo_delay)

    def __repr__(self):
        return "DBA IPACT - freq: {}, free_time: {}".\
            format(self.freq, self.free_time)

# assign VPON/DBA to requests
class DBA_Assigner(Active_Node, Virtual_Machine):
    def __init__(self, env, node, consumption_rate, max_frequency, enabled=True, delay=0):
        self.env = env
        self.node = node
        self.max_frequency = max_frequency
        self.delay = delay

        self.available_freq = 0
        self.dbas = []

        Active_Node.__init__(self, env, enabled, consumption_rate, [], self.env.now)

    def func(self, o):
        if(type(o) is Request):
            print(str(self), "received", str(o), "at", self.env.now)
            # search request's dba (if possible)
            target_dba = None
            yield self.env.timeout(self.delay)
            for d in self.dbas:
                if(o.id_sender in d.onus): # found!
                    print(str(self) + ": this ONU has already a DBA")
                    return o
                if(target_dba == None and d.bandwidth - d.bandwidth_used + o.bandwidth >= 0):
                    target_dba = d
            # not fonud! create/assign new VPON/DBA
            print(str(self) + ": this ONU hasn't a DBA")
            if(target_dba == None):
                # create
                print(str(self) + ": Creating DBA")
                target_dba = DBA_IPACT(self.env, self.node, 0, self.available_freq, DBA_IPACT_default_bandwidth) # DBA_IPACT_default_bandwidth
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
                print(str(self) + ": Assigning DBA")
                # assign
                target_dba.associate_onu(o)
        return o

    def __repr__(self):
        return "DBA Assigner - (n/a)"