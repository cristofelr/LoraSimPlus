import random
import numpy as np
import ParameterConfig
from Propagation import rssi, snr
from Packet import myPacket

def random_allocation():
    sf = random.randint(7,12)
    bw = random.choice([125,250,500])
    fre = random.choice(ParameterConfig.Carrier_Frequency)
    return sf,bw,fre

#choose the closest SF and bw config according to distance between node and gateway and receive sensitivity
def closest_allocation(distance):
    RSSI = rssi(distance)
    SNR = snr(RSSI)
    
    # Search from most efficient (SF7, BW500) to most robust (SF12, BW125)
    for sf in range(7, 13):
        # BW 500 is the most efficient (least sensitive), 125 is least efficient (most sensitive)
        # So we check 500, then 250, then 125.
        for bw in [500, 250, 125]:
            if RSSI > myPacket.GetReceiveSensitivity(sf, bw) and SNR > myPacket.GetMiniSNR(sf):
                return sf, bw, random.choice(ParameterConfig.Carrier_Frequency)
                
    # Fallback for extreme distances
    return 12, 125, random.choice(ParameterConfig.Carrier_Frequency)

def polling_allocation(id):
    nodeid = id
    nodeid = nodeid % 48
    sf = (nodeid // 8) + 7
    fre_index = nodeid % 8
    fre = ParameterConfig.Carrier_Frequency[fre_index]
    bw = random.choice([125,250,500])
    return sf,bw,fre



            



