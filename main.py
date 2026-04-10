import sys
import ParameterConfig
from simulation import Simulation
from datetime import datetime

if __name__ == "__main__":
    # get arguments
    if len(sys.argv) > 1:
        ParameterConfig.nrNodes = int(sys.argv[1])              # number of nodes                      
        ParameterConfig.avgSendTime = int(sys.argv[2])          # average sending interval in milliseconds
        ParameterConfig.allocation_type = sys.argv[3]           # "Local" | "Global"
        ParameterConfig.allocation_method = sys.argv[4]         # allocation method for LoRa parameters
        ParameterConfig.simtime = int(sys.argv[5])              # total running time in milliseconds
        ParameterConfig.nrBS = int(sys.argv[6])                 # number of base stations 1,2,3,4,6,8,24
        if len(sys.argv) > 7:
            ParameterConfig.full_collision = bool(int(sys.argv[7]))  # 1 = full collision check
        if len(sys.argv) > 8:
            ParameterConfig.directionality = int(sys.argv[8])   # 1 = directional antennae
        if len(sys.argv) > 9:
            ParameterConfig.nrNetworks = int(sys.argv[9])       # number of networks
        if len(sys.argv) > 10:
            ParameterConfig.radius = float(sys.argv[10])        # radius of network (m)
        if len(sys.argv) > 11:
            ParameterConfig.PayloadSize = int(sys.argv[11])     # payload size (bytes)
        # ---- Optional clustering parameters ----
        if len(sys.argv) > 12:
            ParameterConfig.clustering_enabled = bool(int(sys.argv[12]))   # 1 = enable clustering
        if len(sys.argv) > 13:
            ParameterConfig.nrClusters = int(sys.argv[13])                 # number of clusters (K-means)
        if len(sys.argv) > 14:
            ParameterConfig.clustering_algorithm = sys.argv[14]            # "kmeans" | "leach" | "kde_kmeans"
        if len(sys.argv) > 15:
            ParameterConfig.leach_ch_prob = float(sys.argv[15])            # CH probability (LEACH)
        if len(sys.argv) > 16:
            ParameterConfig.leach_rounds = int(sys.argv[16])               # LEACH rounds
        if len(sys.argv) > 17:
            ParameterConfig.node_initial_energy = float(sys.argv[17])      # Initial energy
        if len(sys.argv) > 18:
            ParameterConfig.graphics = int(sys.argv[18])                   # 0 = off, 1 = on
        if len(sys.argv) > 19:
            ParameterConfig.ch_selection = sys.argv[19]                    # "centroid" | "energy_proximity" | "default"
        if len(sys.argv) > 20:
            ParameterConfig.cross_validate = bool(int(sys.argv[20]))       # 0 | 1
        if len(sys.argv) > 21:
            ParameterConfig.n_folds = int(sys.argv[21])                    # number of folds
    else:
        print ("------Use the default config------")

    print ("Graphics enabled: ", ParameterConfig.graphics)

    print ("Nodes per base station:", ParameterConfig.nrNodes) 
    print ("AvgSendTime (exp. distributed):", ParameterConfig.avgSendTime)
    print ("LoRa parameters allocation type: ", ParameterConfig.allocation_type)
    print ("LoRa parameters allocation method: ", ParameterConfig.allocation_method)
    print ("Simtime: ", ParameterConfig.simtime)
    print ("nrBS: ", ParameterConfig.nrBS)
    print ("Full Collision: ", ParameterConfig.full_collision)
    print ("with directionality: ", ParameterConfig.directionality)
    print ("nrNetworks: ", ParameterConfig.nrNetworks)
    print ("radius: ", ParameterConfig.radius)
    print ("PayloadSize: ", ParameterConfig.PayloadSize)
    print ("Clustering enabled: ", ParameterConfig.clustering_enabled)
    if ParameterConfig.clustering_enabled:
        print ("Clustering algorithm: ", ParameterConfig.clustering_algorithm)
        if ParameterConfig.clustering_algorithm in ["kmeans", "kde_kmeans"]:
            print("Number of clusters: ", ParameterConfig.nrClusters)
            if ParameterConfig.cross_validate:
                print(f"K-Fold Cross-Validation: Enabled ({ParameterConfig.n_folds} folds)")
        elif ParameterConfig.clustering_algorithm == "leach":
            print("LEACH CH probability: ", ParameterConfig.leach_ch_prob)
            print("LEACH rounds: ", ParameterConfig.leach_rounds)
            print("Initial energy: ", ParameterConfig.node_initial_energy)

    ParameterConfig.setup_graphics()

    simulation = Simulation()
    simulation.simstarttime = datetime.now()
    simulation.run()
    simulation.simendtime = datetime.now()
    simulation.results_calculation()
    simulation.results_show()
    simulation.simulation_record()
    
