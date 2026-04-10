import random
import os
import matplotlib.pyplot as plt
import ParameterConfig
from Propagation import checkcollision
from Gateway import myBS
from Node import myNode
from datetime import datetime
from Clustering import Clustering

class Simulation:
    def __init__(self):
        self.sum = 0
        self.sumSent = 0
        self.sent = []
        self.der = []
        self.simstarttime = 0
        self.simendtime = 0
        self.avgDER = 0
        self.derALL = 0
        self.RecPacketSize = 0
        self.TotalPacketSize = 0
        self.TotalPacketAirtime = 0
        self.TotalEnergyConsumption = 0
        self.throughput = 0
        self.EffectEnergyConsumPerByte = 0
        self.file_name = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.folder_path = os.path.join(os.getcwd(), "results")
        self.folder_path = os.path.join(self.folder_path,self.file_name)
        if not os.path.exists(self.folder_path):
            os.makedirs(self.folder_path)

    def run(self):
         
        logfile = os.path.join(self.folder_path, "link_metrics.txt")
        with open(logfile, "w") as f:
            f.write("node;gateway;RSSI;SNR;TOA;SF;BW;TXPOWER;FREQ;CHANNEL;DISTANCE;ENERGY;STATUS;ROLE\n") 
        # generate BS
        for i in range(0, ParameterConfig.nrBS):
            b = myBS(i)
            ParameterConfig.bs.append(b) # append the BS to the list
            # append new list for each BS
            ParameterConfig.packetsAtBS.append([]) 
            ParameterConfig.packetsRecBS.append([])

        # generate node
        node_id = 0
        while len(ParameterConfig.nodes) < ParameterConfig.nrNodes * ParameterConfig.nrBS:
            # myNode takes period (in ms), base station id packetlen (in Bytes)
            # 1000000 = 16 min
            x = random.randint(-ParameterConfig.radius, ParameterConfig.radius)
            y = random.randint(-ParameterConfig.radius, ParameterConfig.radius)
            # make sure the nodes are inside the circle
            if (x ** 2 + y ** 2) > (ParameterConfig.radius ** 2):
                continue
            for j in range(0, ParameterConfig.nrBS):
                # create nrNodes for each base station
                node = myNode(node_id * ParameterConfig.nrBS + j, x, y, ParameterConfig.avgSendTime, ParameterConfig.bs[j]) 
                ParameterConfig.nodes.append(node)
                
                # when we add directionality, we update the RSSI here
                if (ParameterConfig.directionality == 1):
                    node.updateRSSI()
                ParameterConfig.env.process(Simulation.transmit(self, ParameterConfig.env, node)) 
            node_id += 1

        # ---- Clustering -----------------------------------------------
        if ParameterConfig.clustering_enabled:
            # Use only the unique physical nodes (one per spatial position)
            # The simulator duplicates nodes across BSs; cluster on distinct
            # positions (nodes assigned to bs[0] are the unique ones).
            unique_nodes = [n for n in ParameterConfig.nodes if n.bs.id == 0]
            clust = Clustering(
                algorithm=ParameterConfig.clustering_algorithm,
                nr_clusters=ParameterConfig.nrClusters,
                leach_ch_prob=ParameterConfig.leach_ch_prob,
                leach_rounds=ParameterConfig.leach_rounds,
                node_initial_energy=ParameterConfig.node_initial_energy,
                ch_selection_method=ParameterConfig.ch_selection,
            )
            
            if ParameterConfig.cross_validate:
                clust.cross_validate(unique_nodes, n_folds=ParameterConfig.n_folds)
                
            clust.run(unique_nodes, gateways=ParameterConfig.bs)
            self.clustering = clust

            # Propagate cluster assignments to duplicated BS copies
            for node in ParameterConfig.nodes:
                if node.bs.id != 0:
                    ref = next((n for n in unique_nodes
                                if n.x == node.x and n.y == node.y), None)
                    if ref:
                        node.cluster_id = ref.cluster_id
                        node.is_ch = ref.is_ch
                        node.parent_ch = ref.parent_ch

            # Save CSV metrics (rounds + per-node energy)
            clust.save_metrics(self.folder_path, self.file_name)

            # Render and save cluster plot (also shows on screen if graphics==1)
            clust.plot(self.folder_path, self.file_name, gateways=ParameterConfig.bs, show=(ParameterConfig.graphics==1))

            # Also colour CHs in the LoRaSim network plot (if graphics on)
            if ParameterConfig.graphics == 1:
                for ch in clust.cluster_heads:
                    ParameterConfig.ax.add_artist(plt.Circle((ch.x, ch.y), 8,
                                             fill=True, color='yellow'))
        else:
            self.clustering = None
        # ---------------------------------------------------------------

        node_path = os.path.join(self.folder_path, self.file_name+"-node.txt")
        with open(node_path, 'w') as nfile:
            for node in ParameterConfig.nodes:
                nfile.write('{x} {y} {id}\n'.format(**vars(node)))

        basestation = os.path.join(self.folder_path, self.file_name+"-basestation.txt")
        with open(basestation, 'w') as bfile:
            for b in ParameterConfig.bs:
                bfile.write('{x} {y} {id}\n'.format(**vars(b)))

        #prepare show
        if (ParameterConfig.graphics == 1):
            plt.xlim([-ParameterConfig.radius, ParameterConfig.radius])
            plt.ylim([-ParameterConfig.radius, ParameterConfig.radius])
            plt.draw()
            plt.show()  
            
        # start simulation
        ParameterConfig.env.run(until=ParameterConfig.simtime)

        # SAVE PERFORMANCE METRICS AFTER SIMULATION
        if ParameterConfig.clustering_enabled and self.clustering:
            self.clustering.save_performance_metrics(self.folder_path, self.file_name, ParameterConfig.PayloadSize)

    def results_calculation(self):
        for i in range(0, ParameterConfig.nrBS):
            self.sum = self.sum + len(ParameterConfig.packetsRecBS[i]) # calculate total received packets
        for i in range(0, ParameterConfig.nrBS):
            self.sent.append(0)
        for i in range(0, ParameterConfig.nrNodes * ParameterConfig.nrBS):
            self.sumSent = self.sumSent + ParameterConfig.nodes[i].sent
            self.sent[ParameterConfig.nodes[i].bs.id] = self.sent[ParameterConfig.nodes[i].bs.id] + ParameterConfig.nodes[i].sent

        self.derALL = 100*(len(ParameterConfig.recPackets)/float(self.sumSent))
        self.sumder = 0
        for i in range(0, ParameterConfig.nrBS):
            self.der.append(100*(len(ParameterConfig.packetsRecBS[i])/float(self.sent[i])))
            self.sumder = self.sumder + self.der[i]
        self.avgDER = (self.sumder)/ParameterConfig.nrBS

        self.throughput = 8 * float(self.RecPacketSize) / self.TotalPacketAirtime
        self.EffectEnergyConsumPerByte = float(self.TotalEnergyConsumption) / self.RecPacketSize
    
    def results_show(self):
        # print stats and save into file
        print ("Number of received packets (independent of right base station)", len(ParameterConfig.recPackets))
        print ("Number of collided packets", len(ParameterConfig.collidedPackets))
        print ("Number of lost packets (not correct)", len(ParameterConfig.lostPackets))
        print ("Total number of packets sent: ", self.sumSent)

        for i in range(0, ParameterConfig.nrBS):
            print ("send to BS[",i,"]:", self.sent[i]) # number of packets sent to each BS
        print ("sent packets: ", ParameterConfig.packetSeq) # total sent packets of nodes
        for i in range(0, ParameterConfig.nrBS):
            print ("packets at BS",i, ":", len(ParameterConfig.packetsRecBS[i])) # received packets of each BS
        print ("overall received at right BS: ", self.sum)

        for i in range(0, ParameterConfig.nrBS):
            print ("DER BS[",i,"]: {:.2f}".format(self.der[i]))    
        print ("avg DER: {:.2f}".format(self.avgDER))
        print ("DER with 1 network:{:.2f}".format(self.derALL))

        print ("Total payload size: {} bytes".format(self.TotalPacketSize))
        print ("Received payload size: {} bytes".format(self.RecPacketSize))
        print ("Total transmission energy consumption: {:.3f} Joule".format(self.TotalEnergyConsumption))
        print ("Network throughput: {:.3f} bps".format(self.throughput))
        print ("Effective energy consumption per byte: {:.3e} Joule".format(self.EffectEnergyConsumPerByte))

        if (ParameterConfig.graphics == 1):
            input('Press Enter to continue ...')
    
    def simulation_record(self):
        result_file_name = self.file_name+"-result.txt"
        file_path = os.path.join(self.folder_path, result_file_name)
        with open(file_path, 'w') as file:
            file.write('Simulation start at {}'.format(self.simstarttime))
            file.write(' and end at {}\n'.format(self.simendtime))
            file.write('--------Parameter Setting--------\n')
            file.write('Nodes per base station: {}\n'.format(ParameterConfig.nrNodes))
            file.write('Packet generation interval: {} ms\n'.format(ParameterConfig.avgSendTime))
            file.write('LoRa parameters allocation type: {}\n'.format(ParameterConfig.allocation_type))
            file.write('LoRa parameters allocation method: {}\n'.format(ParameterConfig.allocation_method))
            file.write('Simulation duration: {} h\n'.format(int(ParameterConfig.simtime/3600000)))
            file.write('Number of gateways: {}\n'.format(ParameterConfig.nrBS))
            if ParameterConfig.full_collision == 1:
                file.write('Collision check mode: Full Collision Check\n')
            else:
                file.write('Collision check mode: Simple Collision Check\n')
            if ParameterConfig.directionality == 1:
                file.write('Antenna type: Directional antenna\n')
            else:
                file.write('Antenna type: Omnidirectional antenna\n')
            file.write('Number of networks: {}\n'.format(ParameterConfig.nrNetworks))
            file.write('Network topology radius: {} m\n'.format(ParameterConfig.radius))
            file.write('Packet payload size: {}\n'.format(ParameterConfig.PayloadSize))
            if ParameterConfig.clustering_enabled:
                file.write('Clustering: enabled\n')
                file.write('Clustering algorithm: {}\n'.format(ParameterConfig.clustering_algorithm))
                if ParameterConfig.clustering_algorithm == "kmeans":
                    file.write('Number of clusters: {}\n'.format(ParameterConfig.nrClusters))
                    file.write('LEACH rounds simulated: 1\n')
                elif ParameterConfig.clustering_algorithm == "leach":
                    file.write('LEACH CH probability: {}\n'.format(ParameterConfig.leach_ch_prob))
                    file.write('LEACH rounds configured: {}\n'.format(ParameterConfig.leach_rounds))
                file.write('Node initial energy: {} J\n'.format(ParameterConfig.node_initial_energy))
                if self.clustering is not None:
                    c = self.clustering
                    file.write('Rounds actually simulated: {}\n'.format(c.total_rounds))
                    if c.first_death_round is not None:
                        file.write('First node death: round {}\n'.format(
                            c.first_death_round))
                    else:
                        file.write('First node death: none (all alive)\n')
                    if c.last_death_round is not None:
                        file.write('Network lifetime (last node death): round {}\n'.format(
                            c.last_death_round))
                    else:
                        file.write('Network lifetime: > {} rounds (network alive)\n'.format(
                            c.total_rounds))
                    if c.round_metrics:
                        last = c.round_metrics[-1]
                        file.write('Alive nodes (final round): {}\n'.format(
                            last['alive_nodes']))
                        file.write('Avg residual energy (final round): {:.4e} J\n'.format(
                            last['avg_residual_energy_J']))
                        file.write('Total residual energy (final round): {:.4e} J\n'.format(
                            last['total_residual_energy_J']))
            else:
                file.write('Clustering: disabled\n')
            file.write('\n')

            file.write('--------Simulation Results--------\n')
            file.write("Total number of packets sent: {}\n".format(self.sumSent))
            file.write("Number of received packets: {}\n".format(len(ParameterConfig.recPackets)))
            file.write("Number of collided packets: {}\n".format(len(ParameterConfig.collidedPackets)))
            file.write("Number of lost packets: {}\n".format(len(ParameterConfig.lostPackets)))
            for i in range(0, ParameterConfig.nrBS):
                file.write("send to BS[{}".format(i))
                file.write("]: {}\n".format(self.sent[i])) # number of packets sent to each BS
            for i in range(0, ParameterConfig.nrBS):
                file.write("packets at BS {}".format(i))
                file.write(": {}\n".format(len(ParameterConfig.packetsRecBS[i]))) # received packets of each BS
            file.write("overall received at right BS: {}\n".format(self.sum))
            for i in range(0, ParameterConfig.nrBS):
                file.write("DER BS[".format(i))
                file.write("]: {:.2f}%\n".format(self.der[i]))    
            file.write("avg DER: {:.2f}%\n".format(self.avgDER))
            file.write("DER with 1 network: {:.2f}%\n".format(self.derALL))
            file.write("Total payload size: {} bytes\n".format(self.TotalPacketSize))
            file.write("Received payload size: {} bytes\n".format(self.RecPacketSize))
            file.write("Total transmission energy consumption: {:.3f} Joule\n".format(self.TotalEnergyConsumption))
            file.write("Network throughput: {:.3f} bps\n".format(self.throughput))
            file.write("Effective energy consumption per byte: {:.3e} Joule\n".format(self.EffectEnergyConsumPerByte))

    @staticmethod       
    def transmit(self, env, node):
        while True:
            # 1. SLEEP: Wait for the next transmission interval
            wait_time = random.expovariate(1.0/float(node.period))
            
            # DUTY CYCLE ENFORCEMENT:
            # Min silence period = ToA * (1/DutyCycle - 1)
            # We use the ToA of the packet for the main BS for calculation
            last_toa = node.packet[0].rectime if len(node.packet) > 0 else 0.0
            min_off_time = last_toa * (1.0 / ParameterConfig.duty_cycle - 1)
            
            # If the random interval is too short, we must wait at least min_off_time
            if wait_time < min_off_time:
                wait_time = min_off_time

            yield env.timeout(wait_time)
            
            # Record sleep time
            node.time_sleep += (env.now - node.last_action_time)
            node.last_action_time = env.now

            # 2. TRANSMIT: send packets to all gateways
            node.sent = node.sent + ParameterConfig.nrBS
            ParameterConfig.packetSeq += ParameterConfig.nrBS

            if ParameterConfig.allocation_type == "Local":
                node.Generate_Packet()
                
            for bs_idx in range(0, ParameterConfig.nrBS):
                if (node in ParameterConfig.packetsAtBS[bs_idx]):
                        print ("ERROR: packet already in")
                else:
                        if (checkcollision(node.packet[bs_idx])==1):
                            node.packet[bs_idx].collided = 1
                        else:
                            node.packet[bs_idx].collided = 0
                        ParameterConfig.packetsAtBS[bs_idx].append(node)
                        node.packet[bs_idx].addTime = env.now
                        node.packet[bs_idx].seqNr = ParameterConfig.packetSeq

                packet = node.packet[bs_idx]
                   
                if packet.lost:
                    status = "LOST"
                elif packet.collided:
                    status = "COLLISION"
                else:
                    status = "RECEIVED"
                channel = packet.fre
                dx = node.x - node.bs.x
                dy = node.y - node.bs.y
                distance = (dx*dx + dy*dy) ** 0.5

                logfile = os.path.join(self.folder_path, "link_metrics.txt")
                with open(logfile, "a") as f:                    
                    role = "CH" if node.is_ch else ("CM" if ParameterConfig.clustering_enabled else "NODE")
                    f.write(
                        f"{node.id};{bs_idx};"
                        f"{packet.RSSI};{packet.SNR};{packet.rectime};"
                        f"{packet.sf};{packet.bw};{packet.tp};"
                        f"{packet.fre};{channel};"
                        f"{distance};"
                        f"{packet.tx_energy};{status};{role}\n"
                    )
                node.node_total_energy += float(node.packet[bs_idx].tx_energy / 1000)
                self.TotalPacketSize += node.packet[bs_idx].PS
                self.TotalPacketAirtime += float(node.packet[bs_idx].rectime / 1000)            
                
                # DETAILED LINK LOGGING (links.csv)
                links_csv = os.path.join(self.folder_path, "links.csv")
                file_exists = os.path.isfile(links_csv)
                with open(links_csv, "a", newline='') as f:
                    import csv
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(['timestamp', 'node_id', 'bs_idx', 'sf', 'bw', 'freq', 'rssi', 'snr', 'toa', 'energy_j', 'status', 'role'])
                    writer.writerow([
                        round(env.now, 2), node.id, bs_idx, 
                        packet.sf, packet.bw, packet.fre, 
                        round(packet.RSSI, 2), round(packet.SNR, 2), 
                        round(packet.rectime, 2), round(packet.tx_energy/1000, 6),
                        status, role
                    ])

            yield env.timeout(node.packet[0].rectime)
            
            # Record TX time and RX windows (simplified Class A)
            # In LoRaWAN, after sending, node stays in RX for a brief moment.
            # For simplicity, we assign the packet airtime to TX.
            node.time_tx += (env.now - node.last_action_time)
            node.last_action_time = env.now
            
            # If the node is a CH (Cluster Head), it might spend more time listening (RX).
            # We'll calculate the RX time at the end or track it here.
            # In this model, let's assume CHs are always Lora-on (RX) when not TX-ing or Sleeping.
            # But here they follow the same TX/Sleep loop, so RX is 0 for standard nodes.

            for bs_idx in range(0, ParameterConfig.nrBS):
                if node.packet[bs_idx].lost:
                    ParameterConfig.lostPackets.append(node.packet[bs_idx].seqNr)
                    node.node_lost += 1
                else:
                    if node.packet[bs_idx].collided == 0:
                        if (ParameterConfig.nrNetworks == 1):
                            ParameterConfig.packetsRecBS[bs_idx].append(node.packet[bs_idx].seqNr)
                            if node.bs.id == bs_idx: node.node_received += 1
                        else:
                            if (node.bs.id == bs_idx):
                                ParameterConfig.packetsRecBS[bs_idx].append(node.packet[bs_idx].seqNr)
                                node.node_received += 1
                        if (ParameterConfig.recPackets):
                            if (ParameterConfig.recPackets[-1] != node.packet[bs_idx].seqNr):
                                ParameterConfig.recPackets.append(node.packet[bs_idx].seqNr)
                                self.RecPacketSize += node.packet[bs_idx].PS
                        else:
                            ParameterConfig.recPackets.append(node.packet[bs_idx].seqNr)
                            self.RecPacketSize += node.packet[bs_idx].PS
                    else:
                        ParameterConfig.collidedPackets.append(node.packet[bs_idx].seqNr)
                        node.node_collided += 1

            # 3. LORAWAN ACK LOGIC (RX Windows)
            # Perform this AFTER checking all base stations for this transmission
            node_packet_at_bs = node.packet[node.bs.id]
            received_by_target = (not node_packet_at_bs.lost and not node_packet_at_bs.collided)
            
            if received_by_target:
                # Wait for RX1 window (1000ms delay after TX end)
                yield env.timeout(1000)
                # Track RX listening time
                rx_listen_duration = 50 # ms 
                node.time_rx += rx_listen_duration
                
                # Assume 95% ACK success probability
                if random.random() < 0.95:
                    node.node_acks_received += 1
                else:
                    # Retry in RX2 (another 1000ms later)
                    yield env.timeout(1000)
                    node.time_rx += rx_listen_duration
                    if random.random() < 0.95:
                        node.node_acks_received += 1
            
            # Record total cycle time alignment for sleep calculation
            node.last_action_time = env.now

            # cleanup for next transmission
            for bs_idx in range(0, ParameterConfig.nrBS):                    
                if (node in ParameterConfig.packetsAtBS[bs_idx]):
                    ParameterConfig.packetsAtBS[bs_idx].remove(node)
                    node.packet[bs_idx].collided = 0
            


    
