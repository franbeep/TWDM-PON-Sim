# chain of virtualized functions 8
import simpy
from abstract_classes import Active_Node
from utils import dprint

class Digital_Unit(Active_Node):
    def __init__(self, env, id, consumption_rate, node, out, vms=None, enabled=False):
        self.id = id
        self.env = env
        self.node = node
        self.res_vms = simpy.Resource(self.env, capacity=1)
        self.vms = vms
        self.out = out
        Active_Node.__init__(self, env, enabled, consumption_rate, vms, self.env.now)

    def __iter__(self):
        return self.vms

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
            d1.out = d

    def append_vm(self, vm): # append vms
        dprint(str(self), "is appending VM", vm, objn=8)
        with self.res_vms.request() as req:
            yield req
            self.vms.append(vm)

    def execute_functions(self, o):
        dprint(str(self), "will execute functions at", self.env.now, objn=8)
        yield self.env.timeout(0)
        if(self.vms == None):
            self.env.process(self.out.send_up(o))
        else:
            for v in self.vms:
                dprint(str(self), "is using VM", str(v), "on", str(o), "at", self.env.now, objn=8)
                o = yield self.env.process(v.func(o))
                dprint(str(self), "returned", str(o), "from execute functions at", self.env.now, objn=8)
                if(o == None):
                    return
            dprint(str(self), "is sending the left data to", str(self.out), "at", self.env.now, objn=8)

            if(type(self.out) is Digital_Unit):
                self.env.process(self.out.execute_functions(o))
            elif(type(self.out) is Processing_Node):
                self.env.process(self.out.send_up(o))

    def __repr__(self):
        return "Digital Unit #{}{}".\
            format(self.node.id, self.id)