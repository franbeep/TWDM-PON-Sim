import sim
import matplotlib.pyplot as plt

sim.DEBUG = True

# seed
sim.random.seed(13)

# default values
sim.tg_default_size = lambda x: 250
sim.tg_default_dist = lambda x: 1
sim.DBA_IPACT_default_bandwidth = 5000
ONU_bitRate_up = sim.DBA_IPACT_default_bandwidth * 8

max_onus = 23

plot1 = max_onus * [0]
plot2 = max_onus * [0]
plot3 = max_onus * [0]

seeds = [2, 3, 5, 7, 13, 17, 19, 23, 29, 31, 61, 67, 71, 73, 79, 83, 89, 97, 101, 107, 109, 113, 127, 131, 163, 167, 173, 179, 181, 317, 331, 337, 347, 349, 353]
# seeds = [2,7,29]

for s in seeds:
    # seed
    sim.random.seed(s)
    lost_req = [0]
    duplicated_req = [0]

    for f in range(1,max_onus+1):
        print("Using seed {", s, "} on ONU {", f, "}")
        # override suffix writer
        sim.packet_w = sim.Writer("# id src init_time waited_time freq processed_time\n")

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

        nodes = sim.create_topology(env, antenas, onus, pns, splts, matrix, max_frequencies)

        # start
        print("\tBegin")
        env.run(until=5)
        print("\tEnd")

        total_lost = 0
        total_duplicated = 0
        for vm in nodes[len(nodes)-2].DU[0].vms:
            if(type(vm) is sim.DBA_IPACT):
                total_lost += vm.discarded_requests
                total_duplicated += vm.duplicated_requests

        lost_req.append(total_lost)
        duplicated_req.append(total_duplicated)

        sim.packet_w.close()

    # read files, generate graph
    mean_waited_array=[0]

    for f in sim.output_files:
        file = open(f, "r")
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

    for i in range(max_onus):
        plot1[i] += lost_req[i] / len(seeds)
        plot2[i] += duplicated_req[i] / len(seeds)
        plot3[i] += mean_waited_array[i] / len(seeds)


figure = plt.figure()

plt.subplot(3, 1, 1)
plt.plot(plot1, 'g.-')
plt.ylabel('Number of Requests Lost')

plt.subplot(3, 1, 2)
plt.plot(plot2, 'b.-')
plt.ylabel('Number of Requests Duplicated')

plt.subplot(3, 1, 3)
plt.plot(plot3, 'r.-')
plt.ylabel('Average waited time (s)')
plt.xlabel('Number of ONUs')

print("Finished")

plt.show()