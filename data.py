# data abstraction
class Packet(object):
    def __init__(self, id, size, src, dst, init_time, freq=-1):
        self.id = id
        self.size = size
        self.src = src
        self.dst = dst
        self.init_time = init_time
        self.waited_time = 0
        self.freq = freq

    def __repr__(self):
        return "Packet [id:{},src:{},init_time:{}]".\
            format(self.id, self.src, self.init_time)