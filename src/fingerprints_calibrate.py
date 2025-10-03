import paho.mqtt.client as mqtt
import numpy as np
from math_mod_2 import DistanceCalc, Kalman2D
import json
import matplotlib.pyplot as plt
import time 

rssi = []
f_rssi = []
calc = None
cur_pos = [0,0]

BEACON_COUNT = 8
CALIBRATION_TIME_S = 30
DISTANCE_METERS = 1.0
MQTT_TOPIC = "ble_rssi/rssi"
MAIN_IP = "127.0.0.1"

collector = {}

def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe("ble_rssi/rssi")
    

def on_message(client, userdata, msg):
    if 'is_collecting' in userdata and not userdata['is_collecting']:
        return

    try:
        data = json.loads(msg.payload.decode("utf-8"))
        
        if "pack" in data:
            for beacon_data in data['pack']:
                name = beacon_data.get('name')
                
                rssi = beacon_data['rssi']
                
                if name and rssi:
                    userdata.setdefault('collector', {}).setdefault(name, []).append(rssi)
                    
    except Exception as e:

        print(f"Error processing message in on_message: {e}")


# calibrate.py -> fingerprints_calibrate

def fingerprints_calibrate():
    print("---FINGERPRINTS CALIBRATION---")
    
    calibration_fingerprints = {}
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    userdata = {'is_collecting': False, 'collector': {}}
    client.user_data_set(userdata)
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect(MAIN_IP, 1883, 60)
    client.loop_start()

    try:
        for i in range(1, BEACON_COUNT + 1):
            point_to_calibrate = f"beacon_{i}"
            
            input(f"\n[ACTION] Please stand at POINT {i} and press Enter...")
            
            userdata['collector'] = {} 
            userdata['is_collecting'] = True 
            
            print(f"Collecting data for {CALIBRATION_TIME_S} seconds for point {point_to_calibrate}...")
            time.sleep(CALIBRATION_TIME_S)
            
            userdata['is_collecting'] = False 

            
            print("Processing data...")
            

            if not userdata['collector']:
                print(f"ERROR: No data collected for point {point_to_calibrate}. Skipping.")
                continue


            point_fingerprint = {}

            for beacon_name, rssi_list in userdata['collector'].items():
                point_fingerprint[beacon_name] = np.median(rssi_list), 2
            

            calibration_fingerprints[point_to_calibrate] = point_fingerprint
            print(f"SUCCESS: Fingerprint for {point_to_calibrate}: {point_fingerprint}")

    except KeyboardInterrupt:
        print("\nCalibration interrupted.")
    finally:
        print("Stopping MQTT client...")
        client.loop_stop()


    if calibration_fingerprints:
        output_file = "fingerprint_config.json"
        with open(output_file, 'w') as f:
            json.dump(calibration_fingerprints, f, indent=4)
        print(f"\nCalibration complete! Saved to {output_file}")




if __name__ == "__main__":
    fingerprints_calibrate()

