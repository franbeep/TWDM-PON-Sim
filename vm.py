from abstract_classes import Virtual_Machine

packet_w = None

class Foo_BB_VM(Virtual_Machine):
    def __init__(self, env, delay=0):
        self.env = env
        self.delay = delay

    def func(self, o):
        if(packet_w != None):
            if(type(o) is Packet):
                packet_w.write("{} {} {} {} {} {}\n".format(o.id, o.src, o.init_time, o.waited_time, o.freq, self.env.now))
            if(type(o) is list and type(o[0]) is Packet):
                for p in o:
                    packet_w.write("{} {} {} {} {} {}\n".format(p.id, p.src, p.init_time, p.waited_time, p.freq, self.env.now))
            yield self.env.timeout(self.delay)
        return None

    def __repr__(self):
        return "Foo BB VM - (n/a)"