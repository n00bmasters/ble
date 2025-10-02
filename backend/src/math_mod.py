import scipy
import numpy as np
from filterpy.kalman import KalmanFilter

UNCERTAINTY = 26

class Kalman:
    def __init__(self):
        kf = KalmanFilter(dim_x=1, dim_z=1)
        kf.x = np.array([0.0])  # initial state
        kf.F = np.array([[1.0]])  # state transition matrix
        kf.H = np.array([[1.0]])  # Measurement function
        kf.P *= 1000.0  # covariance matrix
        kf.R = UNCERTAINTY  # state uncertainty
        self.kf = kf
        self.pushed = 0
        return

    def apply_kalman_filter(self, new_value):
        self.kf.predict()
        self.kf.update(np.array([new_value]))
        return self.kf.x[0]  # This is the filtered value

class DistanceCalc:
    def __init__(self, trans: dict, def_power: list[int]):
        self.trans = trans
        self.def_power = def_power #СУКИ КАЛИБРУЙТЕ ОТ ОДНОЙ НОДЫ, А НЕ ОТ ВСЕХ
        self.scale = 32 
        self.ple = 3

    def get_pos(self, rssis: list[list[int, float]]):
        d = dict()
        #print(available_nodes, rssi)
        rssis.sort(key=lambda x: x[1], reverse=True)
        av = []
        for i in rssis[:3]:
            d[i[0]] = self.get_dist(i[1], i[0])
            av.append(i[0])
        est_x, est_y = self.trilaterate(d, av)
        return est_x, est_y
    
    def trilaterate(self, d, available_nodes):
        def equations(guess):
            x, y, r = guess
            nonlocal d
            system = []
            for i in available_nodes:
                system.append((x - self.trans[i][0]) ** 2 + (y - self.trans[i][1]) ** 2 - (d[i] - r) ** 2)
            return tuple(system)
    
        init = (0,0,0)
        res = scipy.optimize.least_squares(equations, init)
        res = res.x 
        return res[0], res[1]

    def get_dist(self, rssi, i):
        return 10 ** ((self.def_power[i - 1] - rssi) / (10 * self.ple))

#di = DistanceCalc([(0,1), (1,0), (-1, 0)], [-50, -50, -50])
#print(di.get_pos([-50, -49, -46]))
