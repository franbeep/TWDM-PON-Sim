import simpy
import random
import functools

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
        self.freq = 0

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
    def __init__(self, env, id,  adist, sdist, initial_delay=0, finish=float("inf")):
        self.id = id
        self.env = env
        self.adist = adist
        self.sdist = sdist
        self.initial_delay = initial_delay
        self.finish = finish
        self.out = None
        self.packets_sent = 0
        self.action = env.process(self.run())

    def run(self):
        """The generator function used in simulations.
        """
        yield self.env.timeout(self.initial_delay)
        while self.env.now < self.finish:
            # wait for next transmission
            yield self.env.timeout(self.adist())
            self.packets_sent += 1
            p = Packet(self.env.now, self.sdist(), self.packets_sent, src=self.id, flow_id=self.flow_id)

            if(self.id[0] == 'L'): # LC
                self.out.put(p, downstream=True)
            elif(self.id[0] == 'O'): # ONU
                self.out.put(p, upstream=True)

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
            self.out.put(msg)
            self.busy = 0
            if self.debug:
                print msg

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

"""
    Funções do SimComponents
    https://www.grotto-networking.com/DiscreteEventPython.html
"""

####

class LineCard(object):
    def __init__(self, env, lcid, exp, out, distance):
        self.env = env
        self.lcid = lcid
        self.freq = lcid # pra simplificar, ID = frequencia
        self.delay_downstream = distance / float(Light_Speed)
        self.splitter = splitter

        # # para downstream
        # adist = functools.partial(random.expovariate, exp)
        # sdist = functools.partial(random.expovariate, 0.01)
        # self.pg = PacketGenerator(self.env, "LC_PG_" + str(lcid), adist, sdist)
        # self.pg.out = self

        self.downstream = simpy.Store(env)
        self.action = env.process(self.run())

    def put(msg, downstream=False, upstream=False):
        if(downstream):
            self.downstream.put(msg)
        elif(upstream):
            # não faz nada com os pacotes que chegam?
            pass


    def run():
        pass

        # # loop para downstream
        # while True:
        #     yield self.env.timeout(self.delay_downstream)
        #     self.splt.put(self.downstream.get(), downstream=True)

class OLT(object):
    def __init__(self, env, lcs_qty, distance_splitter, distance_lcs, splitters):
        # controller
        self.LCS = []
        self.splitter = Splitter(env, distance_splitter, distance_lcs, splitters)
        for i in range(lcs_qty):
            self.LCS.append(LineCard(self.env, lcid=i, exp=50, splitter=self.splitter, distance=0))
        self.splitter.


    # def gen_scheme():
    #     """
    #         (Re)Gera o esquema de VPONs.
    #     """
    #     pass

class Separator(object):
    pass

class Splitter(object):
    pass

class FstSplitter(object):
    def __init__(self, env, distance_splt, distance_lcs, lcs, splitters):
        self.env = env
        self.delay_downstream = distance_splt / float(Light_Speed)
        self.delay_upstream = distance_lcs / float(Light_Speed)
        self.LCS = lcs # lista de LCS
        self.Splts = splitters # lista de splitters secundarios
        self.relacao_LC_Splt = []

        # m splitters
        self.downstream = []
        for sp in self.Splts:
            self.downstream.append(simpy.Store(env))

    def put(msg, downstream=False, upstream=False):
        if(downstream):
            # utiliza a tabela de relações para mandar a msg (metodo run)
            for i in relacao_LC_Splt[msg.freq]
                self.downstream[i].put(msg)
        elif(upstream):
            # seleciona a mensagem por frequencia
            for lc in LCS:
                if(msg.freq == lc): # chegam direto sem fila
                    yield self.env.timeout(self.delay_upstream)
                    lc.put(msg, upstream=True)
                    break

    def run():
        while True:
            # refazer essa parte
            for i in range(len(self.downstream)):
                self.Splts[i].put(self.downstream[i].get(), downstream=True)

            yield self.env.timeout(self.delay_downstream)

class SecSplitter(object):
    def __init__(self, env, distance_splt, distance_onus, onus, splitter):
        self.ONU_List = onus
        self.delay_downstream = distance_onus / float(Light_Speed)
        self.delay_upstream = distance_splt / float(Light_Speed)
        self.splt = splitter

        self.action = env.process(self.run())

        self.alt_ind = 0
        self.alternate = onus[self.alt_ind].oid

        self.upstream = simpy.Store(env)

    def put(msg, downstream=False, upstream=False):
        if(downstream):
            yield self.env.timeout(self.delay_downstream)
            # broadcast
            for onu in ONU_List:
                onu.put(msg, downstream=True)
        elif(upstream):
            self.upstream.put(msg)

    def run():
        while True:
            yield self.env.timeout(self.delay.upstream)
            self.splt.put(self.upstream.get(), upstream=True)
            self.alt_ind += 1
            if(self.alt_ind == len(ONU_List)):
                self.alt_ind = 0
            self.alternate = onus[self.alt_ind].oid

class ONU(object):
    def __init__(self, env, oid, exp, splitter, freq, distance):
        self.env = env # environment
        self.oid = oid # onu id
        self.freq = freq
        self.splt = splitter
        self.delay_upstream = distance / float(Light_Speed)

        adist = functools.partial(random.expovariate, exp) # tempo de delay para proxima transmissão
        sdist = functools.partial(random.expovariate, 0.01)  # tamanho do packet (~100bytes)

        self.pg = PacketGenerator(self.env, "ONU_PG_" + str(oid), adist, sdist) # gerador de pacotes
        self.pg.out = self

        self.upstream = simpy.Store(env)
        self.action = env.process(self.run())

    def put(msg, downstream=False, upstream=False):
        if(downstream):
            # não faz nada com o pacote que chega
            pass
        elif(upstream):
            self.upstream.put(msg)

    def run():
        while True:
            while self.splt.alternate != self.oid:
                continue
            self.splt.put(self.upstream.get(), upstream=True) # ele vai entregar todos de vez assim
            yield self.env.timeout(self.delay_upstream)



Light_Speed         = 210000
ONU_Queue_Limit     = argv[1]
ONU_Quantity        = argv[2]
Splitters_Ratio     = argv[3]
SIM_DURATION        = argv[4]
RANDOM_SEED         = argv[5]
Distance_OLT_ONU    = 10000.0
