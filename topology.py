from attributes import *
from antenna import Antenna
from onu import ONU
from linecard import LineCard
from processing_node import Processing_Node
from digital_unit import Digital_Unit
from dba import DBA_Assigner
from vm import Foo_BB_VM
from splitter import Splitter
from utils import dprint

def create_topology(env, qnty_ant, qnty_onu, qnty_pn, qnty_splt, matrix, max_frequency):
    id_onu = 0
    id_pn = 0
    id_ant = 0
    id_splt = 0
    nodes = []

    # create nodes
    for i in range(qnty_ant):
        dprint("Creating Antenna #", id_ant)
        nodes.append(Antenna(env, id_ant, None, ANT_CONSUMPTION, 0, 0))
        id_ant += 1

    for i in range(qnty_onu):
        dprint("Creating ONU #", id_onu)
        nodes.append(ONU(env, id_onu, None, None, ONU_CONSUMPTION, None, ONU_BITRATE_UP, ONU_BITRATE_DOWN, 0, threshold=ONU_THRESHOLD))
        id_onu += 1

    for i in range(qnty_pn):
        dprint("Creating Processing Node #", id_pn)
        # create lcs and put them to sleep
        pn_lcs = []
        pn_lcs.append(LineCard(env, -1, enabled=True, consumption=lambda x: 0)) # control's LC
        for j in range(max_frequency):
            pn_lcs.append(LineCard(env, j))
        # create DUs
        pn_dus = []
        # attach LCs and DUs
        pn_node = Processing_Node(env, id_pn, None, None, PN_CONSUMPTION, PN_BITRATE_UP, PN_BITRATE_DOWN, 0, LC=pn_lcs, DU=pn_dus)

        # add a Digital Unit with DBA
        control_du = Digital_Unit(env, 0, DU_COMSUMPTION, pn_node, pn_node, vms=[DBA_Assigner(env, pn_node, 0, max_frequency)], enabled=True)
        pn_node.append_DU(control_du)
        pn_node.attach_DU(0, 0) # attach DU 0 to LC 0 (-1)

        # add a Digital Unit to BB processing (not real BB processing)
        bb_du = Digital_Unit(env, 1, DU_COMSUMPTION, pn_node, pn_node, vms=[Foo_BB_VM(env)])
        pn_node.append_DU(bb_du)

        nodes.append(pn_node)
        id_pn += 1

    for i in range(qnty_splt):
        dprint("Creating Splitter #", id_splt)
        nodes.append(Splitter(env, id_splt, None, None, 0))
        id_splt += 1

    dprint("Total nodes:", len(nodes))

    # connect nodes
    for m in matrix:
        n_one = nodes[m[0]]
        n_two = nodes[m[1]]
        dist = m[2]
        dprint("Attaching", str(n_one), "to", str(n_two), "with a distance of", str(dist))
        n_one.target_up = n_two
        if(type(n_two) is ONU or type(n_two) is Splitter):
            n_two.target_down.append(n_one)
        else:
            n_two.target_down = n_one
        if(type(n_one) is Antenna):
            n_one.delay = dist / float(ANTENNA_SPEED)
        else:
            n_one.delay_up = dist / float(LIGHT_SPEED)

    def set_local_nodes(node):
        if(isinstance(node, Splitter)):
            arr = []
            for t in node.target_down:
                arr += set_local_nodes(t)
            return arr
        elif(isinstance(node, Processing_Node)):
            dprint(str(node), "is a local node")
            return [node]
        else:
            return []

    # set local nodes
    for n in nodes:
        if(isinstance(n, Processing_Node)):
            dprint("Setting local nodes to", str(n), "...")
            n.local_nodes = set_local_nodes(n.target_down)

    return nodes

def create_topology_from_nodes(env, matrix, nodes):
    for m in matrix:
        n_one = nodes[m[0]]
        n_two = nodes[m[1]]
        dist = m[2]
        dprint("Attaching", str(n_one), "to", str(n_two), "with a distance of", str(dist))
        n_one.target_up = n_two
        if(type(n_two) is ONU or type(n_two) is Splitter):
            n_two.target_down.append(n_one)
        else:
            n_two.target_down = n_one
        if(type(n_one) is Antenna):
            n_one.delay = dist / float(ANTENNA_SPEED)
        else:
            n_one.delay_up = dist / float(LIGHT_SPEED)

    # remove all DBAs/VPONs
    for n in nodes:
        if(type(n) is Processing_Node):
            for i in range(len(n.DU)):
                if(type(n.DU[i]) is DBA_IPACT):
                    dprint("Removing DBA IPACT from a DU")
                    n.DU.remove(n.DU[i])
                    i = i - 1

    return nodes