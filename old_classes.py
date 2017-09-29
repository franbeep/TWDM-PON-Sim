class Request(object):
    def __init__(self, id, id_sender, id_receiver, id_rrh, id_cellsite, requested_time, bandwidth, route, packages, vpon):
        self.id             = id
        self.id_sender      = id_sender # identificador do transmissor :: int
        self.id_receiver    = id_receiver # identificador do receptor :: int
        self.id_rrh         = id_rrh # identificador do(s) RRH(s) :: int []
        self.id_cellsite    = id_cellsite # identificador do cellsite :: int
        self.requested_time = requested_time # fatia do tempo desejado :: double
        self.bandwidth      = bandwidth # largura de banda desejada :: double
        self.route          = route # rota dos nos :: int []
        self.packages       = packages # Packet(s) da requisicao :: Packet []
        self.vpon           = vpon # freq do vpon
        self.freq           = vpon

        def __repr__(self):
            return "Request - id: {}, id_sender: {}, id_receiver: {}, id_rrh: {}, id_cellsite: {}, requested_time: {}, bandwidth: {}, route: {}, packages: {}, vpon: {}, freq: {}".\
                format(self.id, self.id_sender, self.id_receiver, self.id_rrh, self.id_cellsite, self.requested_time, self.bandwidth, self.route, self.packages, self.vpon, self.freq)

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
        yield new_vpon
        return

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
                yield self.env.timeout(self.delay)
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
            yield None
            return
        else:
            yield r
            return

    def __repr__(self):
        return "DBA_default - (n/a)"

# use the grant(s) you received
    def use_grant(self, grant):
        sorted(grants, key=lambda grant: grant.init_time) # organiza do menor pro maior
        print(str(grants))
        data_to_transfer = []
        for g in grants:
            # yield self.env.timeout(g.init_time - self.env.now)
            if(self.ack < g.ack):
                self.ack = g.ack
            to_wait = g.init_time - self.env.now
            # if(to_wait < 0):
            #     to_wait = 0
            print(str(self), "is going to wait", str(to_wait), "at", self.env.now)
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

            yield self.env.timeout(to_wait)
            yield self.env.process(self.send_up(data_to_transfer))
        with self.res_grants.request() as req:
            yield req
            self.gran