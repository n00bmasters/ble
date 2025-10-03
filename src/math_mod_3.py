# backend/src/math_mod_2.py

import scipy
import numpy as np
from filterpy.kalman import KalmanFilter

class Kalman2D:
    def __init__(self, dt=1.0, std_acc=1.0, x_std_meas=0.3, y_std_meas=0.3):
        self.kf = KalmanFilter(dim_x=4, dim_z=2)
        self.kf.F = np.array([[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]])
        self.kf.H = np.array([[1, 0, 0, 0], [0, 1, 0, 0]])
        self.kf.R = np.array([[x_std_meas**2, 0], [0, y_std_meas**2]])
        G = np.array([[0.5*dt**2], [0.5*dt**2], [dt], [dt]])
        self.kf.Q = G @ G.T * std_acc**2
        self.kf.P *= 1000.0
    def predict(self): self.kf.predict()
    def update(self, m): self.kf.update(m)
    def initialize_state(self, x, y): self.kf.x = np.array([x, y, 0., 0.])

class PositionCalculator:
    def __init__(self, beacon_positions: dict, tx_powers: list[int]):
        self.trans = beacon_positions
        self.def_power = tx_powers
        self.ple = 4.0 # ТЮНИМ ЕГО
        print("Initialized with ROBUST TRILATERATION method.")

    def get_dist(self, rssi, beacon_id):
        if 0 <= beacon_id - 1 < len(self.def_power):
            tx_power = self.def_power[beacon_id - 1]
            if rssi > tx_power: return 0.5
            return 10 ** ((tx_power - rssi) / (10 * self.ple))
        return float('inf')

    def get_pos(self, beacon_measurements):
        beacon_measurements.sort(key=lambda x: x['std_dev'])
        
        best_beacons = beacon_measurements[:4]
        
        measurements_for_trilateration = []
        for beacon in best_beacons:
            dist = self.get_dist(beacon['rssi'], beacon['id'])
            weight = 1.0 / (beacon['std_dev'] + 0.1)
            
            measurements_for_trilateration.append({
                'id': beacon['id'],
                'dist': dist, 
                'weight': weight
            })
        
        if len(measurements_for_trilateration) < 3:
            return float('nan'), float('nan')

        est_x, est_y = self._trilaterate(measurements_for_trilateration)
        return est_x, est_y
    
    def _trilaterate(self, measurements):
        def equations(guess):
            x, y = guess
            system = []
            for m in measurements:
                pos = self.trans[m['id']]
                error = ((x - pos[0])**2 + (y - pos[1])**2 - m['dist']**2) * m['weight']
                system.append(error)
            return system
        
        initial_guess = np.mean([self.trans[m['id']] for m in measurements], axis=0)
        res = scipy.optimize.least_squares(equations, initial_guess, bounds=([-10, -10], [50, 50]))
        return res.x[0], res.x[1]