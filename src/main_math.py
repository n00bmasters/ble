# src/main_math.py

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
    def __init__(self, beacon_positions: dict, fingerprints: dict):
        self.beacon_positions = beacon_positions
        self.fingerprints = fingerprints
        self.k_neighbors = 3  # TUNE
        print("Initialized with WEIGHTED K-NEAREST NEIGHBORS (Fingerprinting) method.")

    def get_pos(self, beacon_measurements):
        current_rssi_vector = {f"beacon_{m['id']}": m['rssi'] for m in beacon_measurements}
        
        point_errors = []
        for point_name, fingerprint_vector in self.fingerprints.items():
            error = 0
            common_beacons_count = 0
            for beacon_name, calibrated_rssi in fingerprint_vector.items():
                if beacon_name in current_rssi_vector:
                    error += (calibrated_rssi - current_rssi_vector[beacon_name])**2
                    common_beacons_count += 1
            
            if common_beacons_count >= 3:
                normalized_error = error / common_beacons_count
                point_errors.append({'name': point_name, 'error': normalized_error})

        if not point_errors:
            return float('nan'), float('nan')

        point_errors.sort(key=lambda x: x['error'])
        k_nearest_neighbors = point_errors[:self.k_neighbors]

        total_weight = 0
        weighted_x = 0
        weighted_y = 0

        for neighbor in k_nearest_neighbors:
            point_name = neighbor['name']
            error = neighbor['error']
            
            # Превращаем ошибку в "вес доверия". Чем меньше ошибка, тем больше вес.
            weight = 1.0 / (error + 0.001)
            
            beacon_id = int(point_name.split('_')[1])
            position = self.beacon_positions[beacon_id]
            
            weighted_x += position[0] * weight
            weighted_y += position[1] * weight
            total_weight += weight

        if total_weight == 0:
            return float('nan'), float('nan')

        final_x = weighted_x / total_weight
        final_y = weighted_y / total_weight
        
        return final_x, final_y