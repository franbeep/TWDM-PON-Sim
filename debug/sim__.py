import simpy
import random
import functools
import sys

Light_Speed         = 210000

class Packet(object):
    """ A very simple class that represents a packet.
        This packet will run through a queue at a switch output port.
        We use a float to represent the size of the packet in bytes so that
        we can compare to ideal M/M/1 queues.

        Parameters
        ----------
        time : float
            the time the packet arrives at the output queue.
        size : float
            the size of the packet in bytes
        id : int
            an identifier for the packet
        src, dst : int
            identifiers for source and destination
        flow_id : int
            small integer that can be used to identify a flow
    """
    def __init__(self, time, size, id, src="a", dst="z", flow_id=0):
        # generation time
        self.time = time
        # packet size in bytes
        self.size = size
        self.id = id
        # source
        self.src = src
        # destination
        self.dst = dst
        self.flow_id = flow_id
        self.freq = -1

    def __repr__(self):
        return "id: {}, src: {}, time: {}, size: {}".\
            format(self.id, self.src, self.time, self.size)

class PacketGenerator(object):
    """ Generates packets with given inter-arrival time distribution.
        Set the "out" member variable to the entity to receive the packet.

        Parameters
        ----------
        env : simpy.Environment
            the simulation environment
        adist : function
            a no parameter function that returns the successive inter-arrival times of the packets
        sdist : function
            a no parameter function that returns the successive sizes of the packets
        initial_delay : number
            Starts generation after an initial delay. Default = 0
        finish : number
            Stops generation at the finish time. Default is infinite


    """
    def __init__(self, env, id,  adist, sdist, initial_delay=0, finish=float("inf"), flow_id=0):
        self.id = id
        self.env = env
        self.adist = adist
        self.sdist = sdist
        self.initial_delay = initial_delay
        self.finish = finish
        self.out = None
        self.packets_sent = 0
        self.action = env.process(self.run())
        self.flow_id = flow_id

    def run(self):
        """The generator function used in simulations.
        """
        yield self.env.timeout(self.initial_delay)
        while self.env.now < self.finish:
            # wait for next transmission
            yield self.env.timeout(self.adist())
            self.packets_sent += 1
            p = Packet(self.env.now, self.sdist(), self.packets_sent, src=self.id, flow_id=self.flow_id)

            # if(self.id[0] == 'L'): # LC
            #     self.out.put(p, downstream=True)
            # elif(self.id[0] == 'O'): # ONU
            #     self.out.put(p, upstream=True)
            self.out.put(p)

class SwitchPort(object):
    """ Models a switch output port with a given rate and buffer size limit in bytes.
        Set the "out" member variable to the entity to receive the packet.

        Parameters
        ----------
        env : simpy.Environment
            the simulation environment
        rate : float
            the bit rate of the port
        qlimit : integer (or None)
            a buffer size limit in bytes for the queue (does not include items in service).

    """
    def __init__(self, env, rate, qlimit=None, debug=False):
        self.store = simpy.Store(env)
        self.rate = rate
        self.env = env
        self.out = None
        self.packets_rec = 0
        self.packets_drop = 0
        self.qlimit = qlimit
        self.byte_size = 0  # Current size of the queue in bytes
        self.debug = debug
        self.busy = 0  # Used to track if a packet is currently being sent
        self.action = env.process(self.run())  # starts the run() method as a SimPy process

    def run(self):
        while True:
            msg = (yield self.store.get())
            self.busy = 1
            self.byte_size -= msg.size
            yield self.env.timeout(msg.size*8.0/self.rate)
            if(msg.src[0] == 'L'): # LC
                self.out.put(msg, downstream=True)
            elif(msg.src[0] == 'O'): # ONU
                self.out.put(msg, upstream=True)
            self.busy = 0
            if self.debug:
                print(msg)

    def put(self, pkt):
        self.packets_rec += 1
        tmp = self.byte_size + pkt.size

        if self.qlimit is None:
            self.byte_size = tmp
            return self.store.put(pkt)
        if tmp >= self.qlimit:
            self.packets_drop += 1
            return
        else:
            self.byte_size = tmp
            return self.store.put(pkt)

#     Funções do SimComponents
#     https://www.grotto-networking.com/DiscreteEventPython.html

###

class LineCard(object):
    def __init__(self, env, lcid, exp, out=None, distance=0):
        self.env = env
        self.lcid = lcid
        self.freq = lcid # pra simplificar, ID = frequencia
        self.delay_downstream = distance / float(Light_Speed)
        self.out = out

        # # para downstream
        # adist = functools.partial(random.expovariate, exp)
        # sdist = functools.partial(random.expovariate, 0.01)
        # self.pg = PacketGenerator(self.env, "LC_PG_" + str(lcid), adist, sdist)
        # self.pg.out = self

        self.downstream = simpy.Store(env)
        self.upstream = simpy.Store(env)
        # self.action = env.process(self.run())

    def put(self, msg, downstream=False, upstream=False):
        print("LineCard #%d recebeu Packet(src: %s, id: %d)" % (self.lcid, msg.src, msg.id))
        if(downstream):
            yield self.downstream.put(msg)
        elif(upstream):
            yield self.upstream.put(msg) # packets que chegam

    # def run(self):
    #     # # para downstream
    #     # while True:
    #     #     yield self.env.timeout(self.delay_downstream)
    #     #     self.splt.put(self.downstream.get(), downstream=True)
    #     pass

class OLT(object):
    def __init__(self, env, lcs_qty, distance_splitter, distance_lcs, splitters):
        ### controller

        self.env = env
        self.LCS = []

        # create
        self.splitter = Splitter(env, distance_downstream=distance_splitter, distance_upstream=distance_lcs, downstream_target=splitters, frequencies=lcs_qty) # primeiro splitter
        self.separator = Separator(env, lcs_qty)
        for i in range(lcs_qty):
            self.LCS.append(LineCard(self.env, lcid=i, exp=50, out=self.separator))

        # config
        self.separator.LCS = self.LCS
        self.separator.splitter = self.splitter
        self.splitter.upstream_target = self.separator

        self.action = env.process(self.counter())

    def counter(self):
        a = 0
        while True:
            print("\tEnvironment time: " + str(a))
            a += 1
            yield env.timeout(1)

class Separator(object):
    def __init__(self, env, size, LCS=None, splitter=None):
        self.env = env
        self.size = size
        self.LCS = LCS
        self.splitter = splitter

    def put(self, msg, downstream=False, upstream=False):
        if(downstream):
            yield self.env.process(self.splitter.put(msg, downstream=True))
        elif(upstream):
            yield self.env.process(self.LCS[msg.freq].put(msg, upstream=True)) # yield?

class Splitter(object):
    def __init__(self, env, distance_downstream, distance_upstream, downstream_target=None, upstream_target=None, frequencies=0):
        self.env = env
        self.distance_downstream = distance_downstream
        self.distance_upstream = distance_upstream
        self.downstream_target = downstream_target
        self.upstream_target = upstream_target

        self.delay_upstream = distance_upstream / float(Light_Speed)
        self.delay_downstream = distance_downstream / float(Light_Speed)

        self.res = []
        for fr in range(frequencies):
            self.res.append(simpy.Resource(env, capacity=1))

    # self.splitter.put(msg, upstream=True)
    def put(self, msg, downstream=False, upstream=False, carry_delay=0):
        if(downstream):
            for target in downstream_target:
                yield self.env.timeout(self.delay_downstream)
                yield self.env.process(target.put(msg, downstream=True))
        elif(upstream):
            print(">>> Requesting lambda: " + str(msg.freq) + " from: " + str(msg.src) + " at: " + str(self.env.now))
            request = self.res[msg.freq].request()
            yield request
            if(type(self.upstream_target) is Splitter): # ainda não tem delay, usa o carry
                print("2nd Splitter " + str(self) + " resource " + str(msg.freq) + " is owned at " + str(self.env.now))
                print("<<< Accepted request from: " + str(msg.src) + " at: " + str(self.env.now))
                yield self.env.process(self.upstream_target.put(msg, upstream=True, carry_delay=(carry_delay + self.delay_upstream))) # carrega o delay para proximo splitter
            else: # ponto final
                print("1st Splitter " + str(self) + " resource " + str(msg.freq) + " is owned at " + str(self.env.now))
                print("<<< Accepted request from: " + str(msg.src) + " at: " + str(self.env.now))
                yield self.env.timeout(self.delay_upstream + carry_delay)
                yield self.env.process(self.upstream_target.put(msg, upstream=True))
            yield self.res[msg.freq].release(request)
            if(type(self.upstream_target) is Separator):
                print("1st Splitter " + str(self) + " resource " + str(msg.freq) + " is released at " + str(self.env.now))
            else:
                print("2nd Splitter " + str(self) + " resource " + str(msg.freq) + " is released at " + str(self.env.now))

class ONU(object):
    def __init__(self, env, oid, exp, splitter=None, freq=0, distance=0):
        self.env = env # environment
        self.oid = oid # onu id
        self.freq = freq
        self.splitter = splitter
        self.delay_upstream = distance / float(Light_Speed)

        adist = functools.partial(random.expovariate, exp) # tempo de delay para proxima transmissão
        sdist = functools.partial(random.expovariate, 0.01)  # tamanho do packet (~100bytes)

        self.pg = PacketGenerator(self.env, "ONU_PG_" + str(oid), adist, sdist) # gerador de pacotes
        self.sp = SwitchPort(self.env, 10000) # bit rate of 10.000
        self.pg.out = self.sp
        self.sp.out = self

        self.upstream = simpy.Store(env)
        self.downstream = simpy.Store(env)
        self.action = env.process(self.run())

    def put(self, msg, downstream=False, upstream=False):
        if(downstream):
            self.downstream.put(msg)
        elif(upstream):
            self.upstream.put(msg)

    def run(self):
        while True:
            msg = yield self.upstream.get() # quando tiver, pega o packet
            msg.freq = self.freq
            print("Encaminhado Packet (src: %s, id: %d)... " % (msg.src, msg.id))
            yield self.env.process(self.splitter.put(msg, upstream=True))
            # self.splitter.put(msg, upstream=True)

###

# Input do usuario
ONU_queue_limit     = int(sys.argv[1])
ONU_quantity        = int(sys.argv[2])
splitters_ratio     = int(sys.argv[3])
SIM_DURATION        = int(sys.argv[4])
RANDOM_SEED         = int(sys.argv[5])
LCS_quantity        = int(sys.argv[6])
Distance_OLT_ONU    = int(sys.argv[7])
Realtime_factor     = float(sys.argv[8])

# lista as variaveis do simulador
print("\tVariaveis:\nONU_queue_limit:%d\nONU_quantity:%d\nsplitters_ratio:%d\nSIM_DURATION:%d\nRANDOM_SEED:%d\nLCS_quantity:%d\nDistance_OLT_ONU:%d\nRealtime_factor:%f" % (ONU_queue_limit, ONU_quantity, splitters_ratio, SIM_DURATION, RANDOM_SEED, LCS_quantity, Distance_OLT_ONU, Realtime_factor))
print("\t---------")
random.seed(RANDOM_SEED)
splitters_qty = int((ONU_quantity-1) / splitters_ratio) + 1
print("splitters_qty:%s" % splitters_qty)
onus_per_splt = int(ONU_quantity / splitters_qty) + 1
print("onus_per_splt:%s" % onus_per_splt)
onus_per_lc = int(onus_per_splt / LCS_quantity) # ONU qty > LCs qty
print("onus_per_lc:%s" % onus_per_lc)
print("\t---------")
print("\n")

# tipo do environment
env = simpy.rt.RealtimeEnvironment(factor=Realtime_factor)
# env = simpy.Environment()

# cria 2nd splitters:
splitters = []
oid = 0
freq = 0
onus_left = splitters_qty * (onus_per_splt) - ONU_quantity
for i in range(splitters_qty):
    splt = Splitter(env, 0, Distance_OLT_ONU, frequencies=LCS_quantity) # falta upstream target e downstream target
    left = 0
    if(onus_left > 0):
        left = 1
        onus_left -= 1
    # cria onus do splitter
    onus = []
    for e in range(onus_per_splt-left):
        if(oid >= ONU_quantity):
            break
        freq += 1
        if(freq >= LCS_quantity):
            freq = 0
        onus.append(ONU(env, oid=oid, exp=77, splitter=splt, freq=freq))
        oid += 1

    splt.downstream_target = onus
    splitters.append(splt)

#cria OLT (lcs, separator, 1st splitter)
olt = OLT(env, LCS_quantity, Distance_OLT_ONU, 0, splitters)

# atribui 2nd splitters upstream_target:
for splt in splitters:
    splt.upstream_target = olt.splitter

# inicia simulação
print("\n\tStarting Simulation...")
env.run(until=SIM_DURATION)
