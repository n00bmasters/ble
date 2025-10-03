# backend/src/math_mod_2.py

import scipy
import numpy as np
from filterpy.kalman import KalmanFilter

UNCERTAINTY = 28

class Kalman2D:
    def __init__(self, dt=1.0, u_x=0, u_y=0, std_acc=1.0, x_std_meas=0.3, y_std_meas=0.3):
        """
        dt: time step
        u_x, u_y: acceleration components
        std_acc: process noise magnitude
        x_std_meas, y_std_meas: measurement noise standard deviations
        """
        # State vector [x, y, vx, vy]
        self.kf = KalmanFilter(dim_x=4, dim_z=2)
        # State matrix
        self.kf.F = np.array([[1, 0, dt, 0],
                              [0, 1, 0, dt],
                              [0, 0, 1, 0],
                              [0, 0, 0, 1]])
        # Control input matrix
        self.kf.H = np.array([[1, 0, 0, 0],
                              [0, 1, 0, 0]])

        # Covariance matrix
        self.kf.R = np.array([[x_std_meas**2, 0],
                              [0, y_std_meas**2]])
        
        # -- Process noise covariance --
        G = np.array([[0.5*dt**2], [0.5*dt**2], [dt], [dt]])
        self.kf.Q = G @ G.T * std_acc**2

        self.kf.P *= 1000.0  # covariance matrix
        
        return


    def predict(self):
        return self.kf.predict()
    
    def update(self, measurement):  
        return self.kf.update(measurement)
    
    def initialize_state(self, x, y):
        # Initialize state with position (x, y) and zero velocity
        self.kf.x = np.array([x, y, 0., 0.])


# class DistanceCalc:
#     def __init__(self, trans: dict, def_power: list[int]):
#         self.trans = trans
#         self.def_power = def_power #СУКИ КАЛИБРУЙТЕ ОТ ОДНОЙ НОДЫ, А НЕ ОТ ВСЕХ
#         self.scale = 32 
#         self.ple = 4.5

#     def get_pos(self, beacon_measurements):
#         beacon_measurements.sort(key=lambda x: x['std_dev'])
#         best_beacons = beacon_measurements[:3]
#         measurements_for_trilateration = []
#         for beacon in best_beacons: # Preparing data for trilateration
#             dist = self.get_dist(beacon['rssi'], beacon['id']) # 
#             weight = 1.0 / (beacon['std_dev'] + 0.1) # Weight inversely proportional to std_dev
                
#             measurements_for_trilateration.append({
#                 'id': beacon['id'],
#                 'dist': dist, 
#                 'weight': weight
#             })

#         est_x, est_y = self.trilaterate(measurements_for_trilateration)
#         return est_x, est_y
    
#     def trilaterate(self, measurements):
#         def equations(guess):
#             x, y = guess
#             system = []
#             for m in measurements:
#                 beacon_id = m['id']
#                 dist = m['dist']
#                 weight = m['weight']
#                 beacon_pos = self.trans[beacon_id]
                
#                 # Error : ( (x-x_i)^2 + (y-y_i)^2 - d_i^2 ) * weight
#                 error = ((x - beacon_pos[0])**2 + (y - beacon_pos[1])**2 - dist**2) * weight
#                 system.append(error)
#             return system
    
#         # First guess based on the average position of the available nodes
#         initial_guess = np.mean([self.trans[m['id']] for m in measurements], axis=0)
        
#         res = scipy.optimize.least_squares(equations, initial_guess)
#         return res.x[0], res.x[1]

#     def get_dist(self, rssi, i):
#         return 10 ** ((self.def_power[i - 1] - rssi) / (10 * self.ple))

# math_mod_2.py

class DistanceCalc:
    def __init__(self, trans: dict, calibration_data: dict):
        self.beacon_positions = trans
        self.calibration_fingerprints = calibration_data
        print("Initialized with Fingerprinting method.")

    def get_pos(self, beacon_measurements):
        current_rssi_vector = {f"beacon_{m['id']}": m['rssi'] for m in beacon_measurements}

        best_match_point = None
        lowest_distance = float('inf')

        for point_name, fingerprint_vector in self.calibration_fingerprints.items():
            
            current_distance = 0
            common_beacons = 0
            
            for beacon_name, rssi in fingerprint_vector.items():
                if beacon_name in current_rssi_vector:
                    # Считаем сумму квадратов разниц (Евклидово расстояние)
                    error = rssi - current_rssi_vector[beacon_name]
                    current_distance += error**2
                    common_beacons += 1
            
            if common_beacons == 0:
                continue 
            
            normalized_distance = current_distance / common_beacons

            if normalized_distance < lowest_distance:
                lowest_distance = normalized_distance
                best_match_point = point_name


        if best_match_point:
            beacon_id = int(best_match_point.split('_')[1])
            return self.beacon_positions[beacon_id]
        else:

            return float('nan'), float('nan')

#di = DistanceCalc([(0,1), (1,0), (-1, 0)], [-50, -50, -50])
#print(di.get_pos([-50, -49, -46]))
