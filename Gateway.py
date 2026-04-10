import math
import matplotlib.pyplot as plt
import ParameterConfig

class myBS:
    def __init__(self, id):
        self.id = id
        # two-dimensional location 
        self.x = 0
        self.y = 0

        # create gateways and initialize their positions
        if ParameterConfig.nrBS == 1 and self.id == 0:
            self.x = 0
            self.y = 0
        elif ParameterConfig.nrBS == 2:
            a = ParameterConfig.radius/2.0 # radius/2
            if self.id == 0:
                self.x = a
                self.y = 0
            elif self.id == 1:
                self.x = -a
                self.y = 0
        elif ParameterConfig.nrBS == 3:
            a = ParameterConfig.radius/(2.0 + math.sqrt(3)) # radius/11
            b = math.sqrt(3) * a # (9*radius)/11
            c = 2 * a # (2*radius)/11
            if self.id == 0:
                self.x = -b
                self.y = -a
            if self.id == 1:
                self.x = b
                self.y = -a
            if self.id == 2:
                self.x = 0
                self.y = c
        elif ParameterConfig.nrBS == 4:
            a = ParameterConfig.radius/(1.0 + math.sqrt(2)) # radius/5
            if self.id == 0:
                self.x = a
                self.y = a
            if self.id == 1:
                self.x = a
                self.y = -a
            if self.id == 2:
                self.x = -a
                self.y = a
            if self.id == 3:
                self.x = -a
                self.y = -a
                
        if (ParameterConfig.graphics):
            # XXX should be base station position
            # deaw different BSs according to their ids
            if (self.id == 0):
                ParameterConfig.ax.add_artist(plt.Circle((self.x, self.y), 10, fill=True, color='red'))
            if (self.id == 1):
                ParameterConfig.ax.add_artist(plt.Circle((self.x, self.y), 10, fill=True, color='red'))
            if (self.id == 2):
                ParameterConfig.ax.add_artist(plt.Circle((self.x, self.y), 10, fill=True, color='green'))
            if (self.id == 3):
                ParameterConfig.ax.add_artist(plt.Circle((self.x, self.y), 10, fill=True, color='brown'))
