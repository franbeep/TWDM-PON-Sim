import simpy
import functools
import random

rrh_default_dist = functools.partial(random.expovariate, 5.0) # de teste
traffic_gen_default_size = 50
Light_Speed         = 210000 # vel da luz
foo_delay           = 0.0001

# objetos geradores de trafego
# (self, env, id, distribution, hold=None)
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
            print("Traffic Gen. #" + str(self.id) + " time: " + str(self.env.now))
            p = Packet(self.packets_sent, traffic_gen_default_size, self.id, -1, self.env.now)
            print("Gerando " + str(p))
            while(self.hold == None): # se tiver desativado
                yield self.env.timeout(foo_delay)
            self.hold.put(p) # adiciona a array que contem os Packets gerados
            self.packets_sent += 1
            yield self.env.timeout(foo_delay)

# objetos ativos; que consomem energia
# (self, env, enabled, consumption_rate, start_time=0.0)
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
            yield self.env.timeout(foo_delay) # necessario para não entrar em loop infinito

class Antenna(Traffic_Generator, Active_Node):
    def __init__(self, env, id, bitRate, out, distance, enabled=True, rate_dist=rrh_default_dist, consumption_rate=0):
        self.env            = env # environment
        self.id             = id # id da antena
        self.bitRate        = bitRate # taxa de transmissão
        self.out            = out # saida (possivelmente ONU)
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
                if(self.out != None):
                    yield self.env.timeout(pkt.size / (self.self.bitRate * 8)) # delay de encaminhamento
                    yield self.env.timeout(self.delay) # delay de transmissão
                    self.out.put(pkt, up=True) # coloca na onu
            yield self.env.timeout(foo_delay)

class Packet(object):
    def __init__(self, id, size, src, dst, init_time):
        self.id    = id
        self.size  = size # tamanho
        self.src   = src # origem
        self.dst   = dst # destino
        self.init_time = init_time
        self.waited_time = 0 # tempo de espera na fila
        self.freq = -1

    def __repr__(self):
        return "Packet - id: {}, source: {}, destination: {}, init_time: {}, waited_time: {}, size: {}, freq: {}".\
            format(self.id, self.src, self.dst, self.init_time, self.waited_time, self.size, self.freq)

class Request(object):
    def __init__(self, id, id_sender, id_receiver, id_rrh, id_cellsite, requested_time, bandwidth, route, packages, vpon):
        self.id             = id
        self.id_sender      = id_sender # identificador do transmissor :: int
        self.id_receiver    = id_receiver # identificador do receptor :: int
        self.id_rrh         = id_rrh # identificador do(s) RRH(s) :: int []
        self.id_cellsite    = id_cellsite # identificador do cellsite :: int
        self.requested_time = requested_time # fatia do tempo desejado :: double
        self.bandwidth      = bandwidth # largura de banda desejada :: double
        self.route          = route # rota dos nós :: int []
        self.packages       = packages # Packet(s) da requisição :: Packet []
        self.vpon           = vpon # freq do vpon
        self.freq           = vpon

        def __repr__(self):
            return "Request - id: {}, id_sender: {}, id_receiver: {}, id_rrh: {}, id_cellsite: {}, requested_time: {}, bandwidth: {}, route: {}, packages: {}, vpon: {}, freq: {}".\
                format(self.id, self.id_sender, self.id_receiver, self.id_rrh, self.id_cellsite, self.requested_time, self.bandwidth, self.route, self.packages, self.vpon, self.freq)

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

class RRH(Active_Node):
    def __init__(self, env, id, users, consumption_rate, antennas, enabled=True):
        self.env = env
        self.id = id
        self.users = users
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

class VPON(object):
    def __init__(self, onus, freq, now):
        self.onus = onus # onus conectadas
        self.freq = freq # frequencia
        self.free_time = now # tempo em que esta livre

# Grant especifico para DBA
class Grant(object):
    def __init__(self, onu, init_time, size, freq):
        self.onu = onu # onu alvo
        self.init_time = init_time # tempo para começar a transmitir
        self.size = size # tamanho do grant
        self.freq = freq # frequencia para transmitir

# VDBA
class DBA_default(Active_Node):
    def __init__(self, env, vpons, node, consumption_rate, delay=0, enabled=True):
        self.env = env
        self.vpons = vpons
        self.max_per_vpon = 6 # numero maximo de onus por vpon (?)
        self.freq_available = 0 # proxima frequencia disponivel
        self.node = node
        self.delay = delay # delay para execucao da funcao

        Active_Node.__init__(self, env, enabled, consumption_rate, self.env.now)

    def send_grant(self, g):
        self.node.send_down(g)

    # todos os vms tem uma função func
    def func(self, r):
        if(type(r) is Request):
            vpon = None
            self.env.timeout(self.delay)
            if(r.vpon >= 0): # ONU com vpon
                for v in vpons: # acha o vpon da ONU que veio o request
                    if(v.freq == r.vpon):
                        vpon = v
                self.send_grant(Grant(self.free_time + r.requested_time, r.bandwidth, vpon.freq))
            elif(len(vpons) < 0): # nenhum vpon
                vpon = VPON([r.id_sender], self.freq_available, self.env.now) # cria um vpon
                self.freq_available += 1
                self.vpons.append(vpon)
                self.send_grant(Grant(self.env.now + r.requested_time, r.bandwidth, vpon.freq))
            else: # algum vpon e onu nao tem vpon
                for v in vpons: # busca uma vpon que possa colocar onus
                    if(len(v.onus) < self.max_per_vpon):
                        vpon = v
                if(vpon == None): # não ha vpons suficientes
                    vpon = VPON([r.id_sender], self.freq_available, self.env.now)
                    self.vpons.append(vpon)
                    self.freq_available += 1
                self.send_grant(Grant(self.env.now + r.requested_time, r.bandwidth, vpon.freq))
            return None
        else:
            return r

# Splitter passivo; demultiplexador
class Splitter(object):
    def __init__(self, env, id, target_up, target_down, distance_up):
        self.env            = env
        self.id             = id
        self.target_up      = target_up # alvo em upstreaming
        self.target_down    = target_down # alvos em downstreaming
        sorted(self.target_down, key=lambda target: target.delay_up) # organiza pelo tempo de upstreaming dos peers
        self.delay_up       = distance_up / float(Light_Speed) # tempo para transmitir upstream

    def put(self, pkt, down=False, up=False):
        if(down):
            counted = 0
            for t in self.target_down:
                yield self.env.timeout(t.delay_up - counted)
                counted = t.delay_up
                t.put(pkt, down=True)
        if(up):
            yield self.env.timeout(self.delay_up)
            self.target_up.put(pkt, up=True)

class Processing_Node(Active_Node):
    def __init__(self, env, id, consumption_rate, distance_down, distance_up=0, target=None, out=None, enabled=True, DU=None, switch=None, LC=None):
        self.env            = env
        self.id             = id
        self.DU             = DU  # digital units :: Digital_Unit []
        self.LC             = LC
        self.switch         = switch
        self.out            = out   # target upstreaming
        self.target         = target # target downstreaming
        self.delay_up       = distance_up / float(Light_Speed)
        self.delay_down     = distance_down / float(Light_Speed)
        Active_Node.__init__(self, env, enabled, consumption_rate, self.env.now)

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

    def put(self, pkt, down=False, up=False):
        if(down):
            yield self.env.timeout(self.delay_down)
            target.put(pkt, down=True)
        if(up):
            if(enabled):
                target_lc = None
                for l in LC:
                    if(pkt.freq == l.freq):
                        target_lc = l
                        break
                target_lc.put(pkt)
            else: # desativado
                self.send_up(pkt, up=True)

    def send_up(self, o):
        if(out != None): # caso da OLT
            yield self.env.timeout(self.delay_up)
            self.out.put(o, up=True)

    def send_down(self, o):
        yield self.env.timeout(self.delay_down)
        for t in self.targets:
            t.put(o, down=True)

class LineCard(Active_Node):
    def __init__(self, env, delay, freq, out=None, enabled=True, consumption=0):
        self.env = env
        self.delay = delay
        self.freq = freq
        self.out = out
        Active_Node.__init__(self, env, enabled, consumption, self.env.now)

    def put(self, p):
        if(self.out != None and self.enable == True):
            yield self.env.timeout(delay)
            self.out.execute_functions(p)

class ONU(Active_Node):
    def __init__(self, env, id, target, consumption, cellsite, bitRate, rrhs, enabled=True, freq=-1, distance=0, total_distance=0, threshold=0):
        self.env            = env
        self.id             = id
        self.freq           = freq
        self.consumption    = consumption # power consumption
        self.target         = target
        self.cellsite       = cellsite # id cellsite
        self.delay_up       = distance / float(Light_Speed)
        self.rrhs           = rrhs
        self.hold           = [] # pks upstream
        self.grants         = [] # grants recebidos
        self.requests       = [] # requests gerados para serem enviados
        self.request_counting = 0
        self.bitRate        = bitRate # rate de 40gb/s ?
        self.total_distance = total_distance
        self.threshold      = threshold
        Active_Node.__init__(self, env, enabled, consumption, self.env.now)
        self.action         = env.process(self.run()) # loop

    # receiving new packets
    def put(self, pkt, down=False, up=False):
        if(down):
            pass
        if(up):
            self.hold.append(pkt)
            total = 0
            for p in hold:
                total += p.size
            if(total > self.threshold):
                self.gen_request()

    def gen_request(self):
        rrhs = []
        bandwidth = 0
        time_needed = 0
        # requested time seria baseado na distancia total ate OLT? ONU teria como saber isso?
        for p in hold:
            rrhs.append(p.src)
            bandwidth += p.size
        if(self.total_distance <= 0):
            time_needed = -1
        else:
            time_needed = bandwidth * self.bitRate + total_distance / float (Light_Speed)
        self.requests.append(Request(request_counting, self.id, -1, rrhs, self.cellsite, time_needed, bandwidth, -1, self.hold, -1))
        request_counting += 1

    # upstreaming
    def send_up(self, s):
        yield self.env.timeout(s.size / (self.bitRate * 8))
        yield self.env.timeout(self.delay_up)
        self.target.put(s, up=True)

    # downstreaming
    def send_down(self, r):
        if(type(r) is Grant): # grant
            for g in r:
                self.grants.append(g)
        else: # caso em que chegou um Packet
            pass

    def run(self):
        while True:
            if(self.enabled):
                if(len(self.requests) > 0): # envia requests
                    send_up(self.requests.pop())
                if(len(self.grants) > 0): # envia Packets
                    for g in self.grants:
                        if(g.init_time == self.env.now):
                            p = self.hold[0]
                            p.waited_time = self.env.now - p.init_time
                            g.size -= p.size
                            if(g.size >= 0):
                                yield self.env.process(self.send_up(p))
                            if(g.size <= 0):
                                self.grants.remove(g)
                            break
            yield self.env.timeout(foo_delay)

# ainda falta fazer
class Digital_Unit(Active_Node): # execute_functions
    def __init__(self, id, env, consumption_rate, node, out, vms=None, enabled=True):
        self.id = id
        self.env = env
        self.node = node
        self.vms = vms
        self.out = out
        Active_Node.__init__(self, env, enabled, consumption_rate, self.env.now)

    def append(self, vm): # append vms
        self.vms.append(vm)

    def execute_functions(self, o):
        if(self.vms == None):
            return
        else:
            for v in vms:
                o = yield v.func(o)
                if(result == None):
                    break
            if(o != None):
                if(self.out is Digital_Unit):
                    self.out.execute_functions(o)
                else:
                    self.out.send_up(o)

# ainda falta fazer
class Switch(object):
    def config(node, DU, config):
        for tp in config:
            d1 = None
            d2 = None
            for d in DU:
                if(d.id == tp[0]):
                    d1 = d
                if(d.id == tp[1]):
                    d2 = d
            if(d1 == None or d2 == None):
                break
            d1.out = d2
