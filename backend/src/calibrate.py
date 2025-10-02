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

collector = {}

def on_connect(client, userdata, flags, reason_code, properties):
    client.subscribe("ble_rssi/rssi")
    
def on_message(client, userdata, msg):
    global collector
    rssis = []
    old = 0
    meow = msg.payload.decode("utf-8")
    js = json.loads(meow)["pack"]
    for beacon in js:
        name = beacon['name']
        rssi_avg = beacon['rssi_avg']
        collector.setdefault(name, []).append(rssi_avg)
        print(f"{name}: {rssi_avg}")

    #print(js)
    #print(meow)


def calibrate():
    global collector
    tx_power_results = {}
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.connect("10.9.34.158", 1883, 60)
    client.loop_start()

    try:
        for i in range(1, BEACON_COUNT + 1):
            beacon_name_to_calibrate = f"beacon_{i}"
            
            input(f"\n[ACTION] Please stand at {DISTANCE_METERS}m from BEACON {i} and press Enter...")
            
            print(f"Collecting data for {CALIBRATION_TIME_S} seconds for {beacon_name_to_calibrate}...")
            time.sleep(CALIBRATION_TIME_S)
            
            client.unsubscribe(MQTT_TOPIC)
            
            print("Processing data...")
            print(collector)            
            if beacon_name_to_calibrate in collector:
                rssi_list = collector[beacon_name_to_calibrate]
                tx_power = np.median(rssi_list)
                tx_power_results[beacon_name_to_calibrate] = tx_power
                print(f"SUCCESS: Calibrated TxPower for {beacon_name_to_calibrate} is {tx_power_results[beacon_name_to_calibrate]}")
            else:
                print(f"ERROR: No data received from {beacon_name_to_calibrate}. Skipping.")
            collector = {}
            client.subscribe(MQTT_TOPIC)

    except KeyboardInterrupt:
        print("Calibration interrupted.")
    finally:
        client.loop_stop()

    output_file = "tx_power_config.json"
    with open(output_file, 'w') as f:
        json.dump(tx_power_results, f, indent=4)
    print(f"\nCalibration complete! Results saved to {output_file}")




if __name__ == "__main__":
    calibrate()
