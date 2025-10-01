import scipy
import numpy
from filterpy.kalman import KalmanFilter

UNCERTAINTY = 17

def initialize_kalman_filter():
    kf = KalmanFilter(dim_x=1, dim_z=1)
    kf.x = np.array([0.0])  # initial state
    kf.F = np.array([[1.0]])  # state transition matrix
    kf.H = np.array([[1.0]])  # Measurement function
    kf.P *= 1000.0  # covariance matrix
    kf.R = UNCERTAINTY  # state uncertainty
    return kf

def apply_kalman_filter(kf, new_value):
    kf.predict()
    kf.update(np.array([new_value]))
    return kf.x  # This is the filtered value

class DistanceCalc:
    def __init__(self, trans: list[tuple], def_power: list[int]):
        self.trans = trans
        self.def_power = def_power
        self.scale = 32 
        self.ple = 1.8
    def get_pos(self, rssi: list[int]):
        d = []
        for i in range(len(rssi)):
            d.append(self.get_dist(rssi[i], i)) 
        est_x, est_y = self.trilaterate(d)
        return est_x, est_y
    def trilaterate(self, d):
        def equations(guess):
            x, y, r = guess
            nonlocal d
            system = []
            for i in range(len(self.trans)):
                system.append((x - self.trans[i][0]) ** 2 + (y - self.trans[i][1]) ** 2 - (d[i] - r) ** 2)
            return system
    
        init = (0,0,0)
        res = scipy.optimize.least_squares(equations, init)
        res = res.x 
        return res[0], res[1]

    def get_dist(self, rssi, i):
        return 10 ** ((self.def_power[i] - rssi) / (10 * self.ple))

di = DistanceCalc([(0,1), (1,0), (-1, 0)], [-50, -50, -50])
print(di.get_pos([-50, -49, -46]))
