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
