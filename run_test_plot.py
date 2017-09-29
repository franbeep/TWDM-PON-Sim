import sim
import matplotlib.pyplot as plt



max_onus = 20

# seed
sim.random.seed(13)

for f in range(1,max_onus):
    # override suffix writer
    sim.packet_w = sim.Writer("packet_" + str(f) + "_", start="#" + str(f) + " ONUs\n# id src init_time waited_time freq processed_time\n", date=False)

    # environment
    env = sim.simpy.Environment()

    # topology
    antenas = f
    onus = f 
    pns = 1
    splts = 1
    max_frequencies = 10

    matrix = []
    for z in range(f):
        matrix.append([z, f+z, 100000])
        matrix.append([f+z, 2*f+1, 100000])
    matrix.append([2*f+1, 2*f, 100000])

    nodes = sim.create_topology(env, antenas, onus, pns, splts, matrix, max_frequencies,onu_consumption=15, pn_consumption=20, lc_consumption=5)

    # add a Digital Unit with DBA
    nodes[2*f].append_DU(20, nodes[2*f], -1, enabled=True, vms=[sim.DBA_Assigner(env, nodes[2*f], 0, 125000, max_frequencies-3)])

    # add a Digital Unit to BB processing
    nodes[2*f].append_DU(20, nodes[2*f], 0, enabled=True, vms=[sim.Foo_BB_VM(env)])

    # start
    print("\nBegin.\n")
    env.run(until=5)
    print("\nEnd.\n")
    
    sim.packet_w.close()

# read files, generate graph
mean_waited_array=[0]

for f in range(1,max_onus):
    file = open("packet_" + str(f) + "_output.dat", "r")
    total = 0
    lines = 0
    for line in file:
        line_sep = line.split(' ')
        if(line_sep[0][0] == "#"):
            continue
        total += float(line_sep[3])
        lines += 1
    file.close()
    total = total / lines
    mean_waited_array.append(total)

plt.plot(mean_waited_array)
plt.ylabel('Average waited time')
plt.show()