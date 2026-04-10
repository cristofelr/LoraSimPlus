#
# this function creates a node
# generate a node in the network with a random space
import matplotlib.pyplot as plt
import numpy as np
import ParameterConfig
from Packet import myPacket
from Allocation import *

class myNode:
    def __init__(self, id, x, y, period, myBS):
        self.bs = myBS # the BS, which the node needs to send packets to
        self.id = id
        self.period = period

        self.x = x
        self.y = y

        # LoRa parameters the node used to send packets      
        self.sf = None
        self.bw = None
        self.fre = None

        self.packet = []
        self.dist = []

        self.sent = 0

        # ---- Clustering fields (populated by Clustering.run()) ----
        self.cluster_id = None    # index of the cluster this node belongs to
        self.is_ch = False        # True if this node is a Cluster Head
        self.parent_ch = None     # Reference to CH node; None for CHs themselves
        # Performance metrics (filled during simulation)
        self.node_received = 0
        self.node_lost = 0
        self.node_collided = 0
        self.node_total_energy = 0 # Accumulated Joule

        if ParameterConfig.allocation_type == "Global":
            myNode.Generate_Packet(self)

        # graphics for node
        if (ParameterConfig.graphics == 1):
            ax = ParameterConfig.ax
            if (self.id == 0):
                    ax.add_artist(plt.Circle((self.x, self.y), 4, fill=True, color='blue'))
            if (self.id == 1):
                    ax.add_artist(plt.Circle((self.x, self.y), 4, fill=True, color='red'))
            if (self.id == 2):
                    ax.add_artist(plt.Circle((self.x, self.y), 4, fill=True, color='green'))
            if (self.id == 3):
                    ax.add_artist(plt.Circle((self.x, self.y), 4, fill=True, color='brown'))
            if (self.id == 4):
                    ax.add_artist(plt.Circle((self.x, self.y), 4, fill=True, color='orange'))
    
    # node generates "virtual" packets for each gateway
    def Generate_Packet(self):
        self.packet = []
        self.dist = []
        for i in range(0, ParameterConfig.nrBS):
            # When clustering is active:
            #   - CMs use the distance to their CH for parameter allocation
            #     (the physical hop CM->CH determines required SF/BW).
            #   - CHs (and regular nodes) use the distance to the gateway.
            if ParameterConfig.clustering_enabled and not self.is_ch and self.parent_ch is not None:
                d = get_distance(self.x, self.y, self.parent_ch)  
            else:
                d = get_distance(self.x, self.y, ParameterConfig.bs[i])  # distance to gateway
            self.dist.append(d)
            PacketPara = ParameterConfig.LoRaParameters()
            if ParameterConfig.allocation_method == "random":
                PacketPara.sf, PacketPara.bw, PacketPara.fre = random_allocation()
            elif ParameterConfig.allocation_method == "closest":
                PacketPara.sf, PacketPara.bw, PacketPara.fre = closest_allocation(self.dist[i])
            elif ParameterConfig.allocation_method == "polling":
                PacketPara.sf, PacketPara.bw, PacketPara.fre = polling_allocation(self.id)
            self.sf = PacketPara.sf
            self.bw = PacketPara.bw
            self.fre = PacketPara.fre
            self.packet.append(myPacket(self.id, PacketPara, self.dist[i], i))
        # print('node %d' %id, "x", self.x, "y", self.y, "dist: ", self.dist, "my BS:", self.bs.id)

#   directional antenna
#   update RSSI depending on direction
#
    def updateRSSI(self):
        print ("+++++++++uR node", self.id, " and bs ", self.bs.id) 
        print ("node x,y", self.x, self.y)
        print ("main-bs x,y", ParameterConfig.bs[self.bs.id].x, ParameterConfig.bs[self.bs.id].y)
        for i in range(0,len(self.packet)):
            print ("rssi before", self.packet[i].RSSI)
            print ("packet bs", self.packet[i].bs)
            print ("packet bs x, y:", ParameterConfig.bs[self.packet[i].bs].x, ParameterConfig.bs[self.packet[i].bs].y)            
            if (self.bs.id == self.packet[i].bs): # node send packet to its main BS
                print ("packet to main bs, increase rssi ")
                self.packet[i].RSSI = self.packet[i].RSSI + ParameterConfig.dir_30
            else: # node send packet to other BS

                b1 = np.array([ParameterConfig.bs[self.bs.id].x, ParameterConfig.bs[self.bs.id].y]) # position of the main BS
                p = np.array([self.x, self.y]) # position of the node
                b2 = np.array([ParameterConfig.bs[self.packet[i].bs].x, ParameterConfig.bs[self.packet[i].bs].y]) # position of the sending BS

                ba = b1 - p # vector ba
                bc = b2 - p # vector bc
                print (ba)
                print (bc)

                cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
                angle = np.degrees(np.arccos(cosine_angle))

                print ("angle: ", angle)

                if (angle <= 30):
                    print ("rssi increase to other BS: 4")
                    self.packet[i].RSSI = self.packet[i].RSSI + ParameterConfig.dir_30
                elif angle <= 90:
                    print ("rssi increase to other BS: 2")
                    self.packet[i].RSSI = self.packet[i].RSSI + ParameterConfig.dir_90
                elif angle <= 150:
                    print ("rssi increase to other BS: -4")
                    self.packet[i].RSSI = self.packet[i].RSSI + ParameterConfig.dir_150
                else:
                    print ("rssi increase to other BS: -3")
                    self.packet[i].RSSI = self.packet[i].RSSI + ParameterConfig.dir_180
            print ("packet rssi after", self.packet[i].RSSI)

def get_distance(x,y,GW):
     dist = np.sqrt((x-GW.x)*(x-GW.x)+(y-GW.y)*(y-GW.y)) # distance between node and gateway
     return dist

def get_nearest_gw(x,y):
    nearestGateway = None
    nearestDistance = None
    for gateway in ParameterConfig.bs:
        distance = get_distance(x,y,gateway)
        if nearestGateway is None:
            nearestGateway = gateway
            nearestDistance = distance
        elif distance < nearestDistance:
            nearestGateway = gateway
            nearestDistance = distance
    return nearestGateway, nearestDistance