import simpy

class User(object):
    pass

class Pacote(object):
    def __init__(self, band_required, req_latency):
        self.band_required  = band_required
        self.request_latency= req_latency

class PacoteCPRI(Pacote):
    def __init__(self, band_required, req_latency):
        super(band_required, req_latency)

class PacoteCOMP(Pacote):
    def __init__(self, band_required, req_latency):
        super(band_required, req_latency)

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
        self.packages       = packages # pacote(s) da requisição :: Pacote []
        # self.vpon           = vpon # estrutura de dados com info. sobre a VPON e sua VM

class Cellsite(object):
    def __init__(self, env, id, rrh, users):
        self.env            = env # environment do SimPy
        self.id             = id # identificador :: int
        self.rrh            = rrh # conjunto de RRH(s) :: RRH []
        self.users          = users # usuarios atendidos :: User []

class RRH(object):
    def __init__(self, env, id, users, mimo_config, status=False):
        self.env            = env
        self.id             = id
        self.users          = users # usuarios atendidos :: User []
        # self.mimo_config    = mimo_config # configuração MIMO
        self.status         = status # ativado/desativado :: bool

class Processing_Node(object):
    def __init__(self, env, id, servers, status=False):
        self.env            = env
        self.id             = id
        # self.servers        = servers # servidores
        self.status         = status # ativado/desativado :: bool

class Splitter(object):
    def __init__(self, env, id, target_up, target_down, distance_up, distance_down):
        self.env            = env
        self.id             = id
        self.target_up      = target_up # alvo em upstreaming :: Object
        self.target_down    = target_down # alvo em downstreaming :: Object []
        self.delay_up       = distance_up / float(Light_Speed) # tempo para transmitir upstream :: float
        self.delay_down     = distance_down / float(Light_Speed) # tempo para transmitir downstream :: float

    # upstreaming
    def send(self, request):
        yield self.env.timeout(self.delay_up)
        yield self.env.process(target_up.send(request))

    # downstreaming
    def receive(self, request):
        yield self.env.timeout(self.delay_down) # mesma distancia; possivel mudança
        for target in target_down:
            yield self.env.process(target.receive(request))

class VBBU(object):
    def __init__(self, env, target, VPF=[]):
        self.env            = env
        self.target         = target
        self.VPF            = VPF

    def add_function(func):
        self.VPF.append(func)

    def remove_function(func):
        self.VPF.remove(func)


class LineCard(object):
    def __init__(self, env, freq=0, target):
        self.env            = env
        self.freq           = freq # frequencia
        self.target         = target # saida; vBBU

    # upstreaming
    def send(self, request):
        yield self.env.process(target.send(request))


class OLT(object):
    def __init__(self, env):
        self.env            = env
        self.action         = env.process(self.run()) # loop

    def send(self, request):
        pass

    # downstreaming
    def receive(self):
        pass

class ONU(object):
    def __init__(self, env, id, target, freq=0, distance=0):
        self.env            = env
        self.id             = id
        self.freq           = freq
        self.target         = target
        self.delay_up       = distance / float(Light_Speed)

        self.action = env.process(self.run()) # loop

    # upstreaming
    def send(self, request):
        pass

    # downstreaming
    def receive(self):
        pass

    def run(self):
        pass
