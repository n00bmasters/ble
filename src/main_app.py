# src/main_app.py


import paho.mqtt.client as mqtt
import numpy as np
from main_math import PositionCalculator, Kalman2D
import json
import matplotlib.pyplot as plt
from math import dist

calc = None
cur_pos = [0,0]
fl = False
kalman_filter = None

BEACON_COUNT = 8
MQTT_IP = "127.0.0.1"

plt.ion()  # Turn on interactive mode
fig, ax = plt.subplots()
x_data = []
y_data = []
pos_x = []
pos_y = [] 
ax.set_xlabel('X Position')
ax.set_ylabel('Y Position')
ax.set_title('Real-time Position Tracking')
ax.grid(True)

def on_connect(client, userdata, flags, reason_code, properties):
    global calc, kalman_filter, position_plot, f_plot, r_plot, ax, fig
    points = dict()
    client.subscribe("ble_rssi/rssi")
    
    # 1. Загружаем координаты маяков
    with open('../beacons_kpa.beacons', 'r') as fp:
        next(fp)
        for i in fp:
            st, x, y = i.split(';')
            points[int(st[-1])] = tuple(map(float, (x, y)))
    
    try:
        with open('fingerprint_config.json', 'r') as f:
            fingerprints = json.load(f)
    except FileNotFoundError:
        print("FATAL: fingerprint_config.json not found! Please run fingerprint calibration first.")
        return

    with open('../path.path', 'w') as f:
        f.write(f"X;Y\n")
    calc = PositionCalculator(points, fingerprints)
    print(f"Fingerprints: {fingerprints}")


    # -- Kalman setup
    dt = 2.5 # ESP32 timing
    std_acc = 0.5 # acceleration
    x_std_meas = 1.5
    y_std_meas = 1.5
    kalman_filter = Kalman2D(dt, std_acc, x_std_meas, y_std_meas)
    kalman_filter.initialize_state(0, 0)


    beacon_x = [point[0] for point in points.values()]
    beacon_y = [point[1] for point in points.values()]
    beacon_plot = ax.plot(beacon_x, beacon_y, 'b^', markersize=10, label='Beacons')[0]
    
    # Initialize current position plot
    global position_plot, f_plot, r_plot
    position_plot = ax.plot([], [], 'ro', markersize=8, label='Current')[0]
    f_plot = ax.plot([cur_pos[0]], [cur_pos[1]], 'ko', markersize=5, label='Path')[0]
    ax.set_xlabel('X Position')
    ax.set_ylabel('Y Position')
    ax.set_title('Real-time Position Tracking')
    ax.grid(True)
    ax.legend()

    # Set reasonable axis limits based on beacon positions
    if beacon_x and beacon_y:
        margin = 2
        ax.set_xlim(min(beacon_x) - margin, max(beacon_x) + margin)
        ax.set_ylim(min(beacon_y) - margin, max(beacon_y) + margin)


def on_message(client, userdata, msg):
    global cur_pos, fl, kalman_filter, position_plot, fig, calc, f_plot, r_plot

    try:
        data = json.loads(msg.payload.decode("utf-8"))
        
        beacon_measurements = []
        for beacon in data.get("pack", []):
            if beacon.get("count", 0) < 2: continue
            measurement = {
                "id": int(beacon["name"].split('_')[1]),
                "rssi": beacon["rssi"], 
                "std_dev": beacon.get("rssi_std", 5.0)
            }   
            beacon_measurements.append(measurement)

        if len(beacon_measurements) < 3:
            print(f'Less than 3 reliable beacons available ({len(beacon_measurements)} found).')
            return

        # Raw hybrid pos
        raw_pos = calc.get_pos(beacon_measurements)
        if np.isnan(raw_pos[0]):
            print("Could not determine a position.")
            return

        # Kalman filter
        kalman_filter.predict()
        kalman_filter.update(np.array([[raw_pos[0]], [raw_pos[1]]]))
        filtered_state = kalman_filter.kf.x
        if dist(cur_pos, (filtered_state[0], filtered_state[1])) < 7 or not fl:
            cur_pos = [filtered_state[0], filtered_state[1]]
            fl = True
        pos_x.append(cur_pos[0])
        pos_y.append(cur_pos[1])

        print(f"RAW: ({raw_pos[0]:.2f}, {raw_pos[1]:.2f})  |  FILTERED: ({cur_pos[0]:.2f}, {cur_pos[1]:.2f})")

        with open('../path.path', 'a') as f:
            f.write(f"{str(cur_pos[0])};{str(cur_pos[1])}\n")
        # Draw
        f_plot.set_data(pos_x[:-1], pos_y[:-1]) 
        position_plot.set_data([cur_pos[0]], [cur_pos[1]])
        fig.savefig("static/plot.png")
        fig.canvas.draw(); fig.canvas.flush_events()
        print(cur_pos)

    except Exception as e:
        print(f"Error processing message: {e}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_IP, 1883, 60)

client.loop_forever()
