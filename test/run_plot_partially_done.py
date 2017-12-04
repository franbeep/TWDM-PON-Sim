import sim
import matplotlib.pyplot as plt

sim.DEBUG = True

# seed
sim.random.seed(13)

# default values
sim.TG_DEFAULT_SIZE = lambda x: 250
sim.DBA_IPACT_DEFAULT_BANDWIDTH = 5000

max_onus = 3

# seed
sim.random.seed(13)

# for f in range(1,max_onus):
#     # override suffix writer
#     sim.packet_w = sim.Writer("# id src init_time waited_time freq processed_time\n")

#     # environment
#     env = sim.simpy.Environment()

#     # topology
#     antenas = f
#     onus = f 
#     pns = 1
#     splts = 1
#     max_frequencies = 10

#     matrix = []
#     for z in range(f):
#         matrix.append([z, f+z, 100000])
#         matrix.append([f+z, 2*f+1, 100000])
#     matrix.append([2*f+1, 2*f, 100000])

#     nodes = sim.create_topology(env, antenas, onus, pns, splts, matrix, max_frequencies)

#     # start
#     print("\nBegin.\n")
#     env.run(until=5)
#     print("\nEnd.\n")
    
#     sim.packet_w.close()

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

plt.plot(mean_waited_array)
plt.ylabel('Average waited time')
plt.show()