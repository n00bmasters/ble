import paho.mqtt.client as mqtt
import numpy as np
from math_mod_2 import DistanceCalc, Kalman2D
import json
import matplotlib.pyplot as plt
from math import dist

calc = None
cur_pos = [0,0]
kalman_filter = None
#points = {}

BEACON_COUNT = 8

plt.ion()  # Turn on interactive mode
fig, ax = plt.subplots()
x_data = []
y_data = []
line, = ax.plot(x_data, y_data, 'ro-')  # Red circles with lines
ax.set_xlabel('X Position')
ax.set_ylabel('Y Position')
ax.set_title('Real-time Position Tracking')
ax.grid(True)

def on_connect(client, userdata, flags, reason_code, properties):
    global calc, kalman_filter

    points = dict()
    client.subscribe("ble_rssi/rssi")
    with open('../config/standart.beacons', 'r') as fp:
        next(fp)
        for i in fp:
            st, x, y = i.split(';')
            points[int(st[-1])] = tuple(map(float, (x, y)))
        print(points)


    with open('tx_power_config.json', 'r') as f:
        tx_powers = json.load(f)

    # tx_powers = []
    # for i in range(1, BEACON_COUNT + 1):
    #     beacon_name = f'beacon_{i}'
    #     if beacon_name in tx_power_data:
    #         tx_powers.append(tx_power_data[beacon_name])
    #     else:
    #         print(f"WARNING: No calibration data found for {beacon_name}. Using default -60.")
    #         tx_powers.append(-60.0)

    calc = DistanceCalc(points, tx_powers)
    print(f"Using Tx Powers: {tx_powers}")

    # -- Tuning Kalman filter parameters --
    dt=2.5 # дата тайм между измерениями в секундах
    std_acc=0.3 # Mean noise БУДЕМ КАЛИБРОВАТЬ

    # noise measurement in meters .БУДЕМ КАЛИБРОВАТЬ
    x_std_meas = 3.0
    y_std_meas = 3.0

    kalman_filter = Kalman2D(dt, std_acc, x_std_meas, y_std_meas)
    kalman_filter.initialize_state(0, 0)
    beacon_x = [point[0] for point in points.values()]
    beacon_y = [point[1] for point in points.values()]
    beacon_plot = ax.plot(beacon_x, beacon_y, 'b^', markersize=10, label='Beacons')[0]
    
    # Initialize current position plot
    global position_plot, f_plot, r_plot
    
    position_plot = ax.plot([cur_pos[0]], [cur_pos[1]], 'ro', markersize=8, label='Current Position')[0]
    f_plot = ax.plot([cur_pos[0]], [cur_pos[1]], 'ko', markersize=8, label='Filt Position')[0]
    r_plot = ax.plot([cur_pos[0]], [cur_pos[1]], 'go', markersize=8, label='Raw Position')[0]
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
    global cur_pos, kalman_filter, position_plot, fig, calc, f_plot, r_plot
    data_js = json.loads(msg.payload.decode("utf-8"))['pack'] # data from mqtt
    # print(data_js)

    beacon_measurements = [] # List to store valid beacon measurements
    for beacon in data_js:
        if beacon.get('count', 0) < 3:
            continue  # Skip this beacon if it has less than 3 samples
        measurement = {
            "id": int(beacon['name'].split('_')[1]),
            "rssi": beacon['rssi'],
            "std_dev": beacon.get('rssi_std', 5.0)
        }   
        beacon_measurements.append(measurement) # Store valid measurements

    if len(beacon_measurements) < 3:
        print('less than 3 available nodes, fix is not obtained')
    else:
        # ЭТО СУКА СВЕЖИЙ КОД ЕСЛИ ЕГО У ТЕБЯ ЕГО НЕТ ТО ПОШЕЛ НАХУЙ 2
        raw_pos = calc.get_pos(beacon_measurements)
        if np.isnan(raw_pos[0]):
            print("Could not determine a position from fingerprinting.")
            return 
        
        kalman_filter.predict()
        

        kalman_filter.update(np.array([[raw_pos[0]], [raw_pos[1]]]))
        
        filtered_state = kalman_filter.kf.x
        cur_pos = [filtered_state[0], filtered_state[1]] 
        
        print(f"RAW: ({raw_pos[0]:.2f}, {raw_pos[1]:.2f})  |  FILTERED: ({cur_pos[0]:.2f}, {cur_pos[1]:.2f})")

        position_plot.set_data([cur_pos[0]], [cur_pos[1]]) 
        r_plot.set_data([raw_pos[0]], [raw_pos[1]]) 
        f_plot.set_data([filtered_state[0]], [filtered_state[1]]) 
        
        # Refresh the plot
        fig.canvas.draw()
        fig.canvas.flush_events()      
        print(cur_pos)




client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

client.connect("127.0.0.1", 1883, 60)

client.loop_forever()
