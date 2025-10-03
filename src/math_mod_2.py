# math_mod_2.py
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
    def __init__(self, beacon_positions: dict, fingerprints: dict, tx_powers: list[int]):
        self.beacon_positions = beacon_positions
        self.fingerprints = fingerprints
        self.tx_powers = tx_powers
        self.ple = 4.0 # TUNE
        print("Initialized with HYBRID (Fingerprint + Trilateration) method.")

    def get_dist(self, rssi, beacon_id):
        if 0 <= beacon_id - 1 < len(self.tx_powers): # TUNE
            tx_power = self.tx_powers[beacon_id - 1]

            if rssi > tx_power:
                return 0.5 # TUNE
            return 10 ** ((tx_power - rssi) / (10 * self.ple))
        return float('inf')

    def _find_best_matching_point(self, current_rssi_vector):
        # fingerprint check
        best_match_point_name = None
        lowest_error = float('inf')
        for point_name, fingerprint_vector in self.fingerprints.items():
            error, common_beacons = 0, 0
            for beacon_name, calibrated_rssi in fingerprint_vector.items():
                if beacon_name in current_rssi_vector:
                    error += (calibrated_rssi - current_rssi_vector[beacon_name])**2
                    common_beacons += 1
            if common_beacons > 1:
                normalized_error = error / common_beacons
                if normalized_error < lowest_error:
                    lowest_error = normalized_error
                    best_match_point_name = point_name
        return best_match_point_name

    def _trilaterate(self, measurements):
        # default trilarteraion
        def equations(guess):
            x, y = guess
            system = []
            for m in measurements:
                pos = self.beacon_positions[m['id']]
                error = ((x - pos[0])**2 + (y - pos[1])**2 - m['dist']**2) * m['weight']
                system.append(error)
            return system
        initial_guess = np.mean([self.beacon_positions[m['id']] for m in measurements], axis=0)
        res = scipy.optimize.least_squares(equations, initial_guess, bounds=([-10, -10], [50, 50]))
        return res.x[0], res.x[1]

    def get_pos(self, beacon_measurements):
        current_rssi_vector = {f"beacon_{m['id']}": m['rssi'] for m in beacon_measurements}
        
        # --- HARD FILTER ---
        best_match_point = self._find_best_matching_point(current_rssi_vector)
        if not best_match_point:
            return float('nan'), float('nan')
        
        # --- HARD SMART FILTER ---

        relevant_fingerprint = self.fingerprints[best_match_point]
    
        sorted_relevant_beacons = sorted(relevant_fingerprint.items(), key=lambda item: item[1], reverse=True)
        
        # CHOOSE ONLY FROM ZONE
        top_beacon_names = [b[0] for b in sorted_relevant_beacons[:4]]

        # --- Trilateration on filtered ---
        measurements_for_trilateration = []
        for m in beacon_measurements:
            beacon_name = f"beacon_{m['id']}"
            if beacon_name in top_beacon_names:
                dist = self.get_dist(m['rssi'], m['id'])
                weight = 1.0 / (m.get('std_dev', 1.0) + 0.1)
                measurements_for_trilateration.append({'id': m['id'], 'dist': dist, 'weight': weight})
        
        if len(measurements_for_trilateration) < 3:
            beacon_id = int(best_match_point.split('_')[1])
            return self.beacon_positions[beacon_id]

        # Trilateration
        est_x, est_y = self._trilaterate(measurements_for_trilateration)
        return est_x, est_y
    
    