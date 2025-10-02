import paho.mqtt.client as mqtt
import numpy as np
from math_mod_2 import DistanceCalc, Kalman2D
import json
import matplotlib.pyplot as plt


calc = None
cur_pos = [0,0]
kalman_filter = None
#points = {}

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

    calc = DistanceCalc(points, list(json.loads(open('../config/calibrate.beacons').read()).values()))
    print(list(json.loads(open('../config/calibrate.beacons').read()).items()))
    #print(rssi)
    dt=2.5 # дата тайм между измерениями в секундах
    std_acc=2.0 # Mean noise БУДЕМ КАЛИБРОВАТЬ

    # noise measurement in meters .БУДЕМ КАЛИБРОВАТЬ
    x_std_meas = 1.0 
    y_std_meas=1.0

    kalman_filter = Kalman2D(dt, std_acc, x_std_meas, y_std_meas)
    kalman_filter.initialize_state(0, 0)
    beacon_x = [point[0] for point in points.values()]
    beacon_y = [point[1] for point in points.values()]
    beacon_plot = ax.plot(beacon_x, beacon_y, 'b^', markersize=10, label='Beacons')[0]
    
    # Initialize current position plot
    global position_plot
    position_plot = ax.plot([cur_pos[0]], [cur_pos[1]], 'ro', markersize=8, label='Current Position')[0]
    
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
    global cur_pos, kalman_filter, position_plot, fig, calc
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
        raw_pos = calc.get_pos(beacon_measurements)
        print(f"RAW POS:{raw_pos}")

        kalman_filter.predict()


        kalman_filter.update(np.array([[raw_pos[0]], [raw_pos[1]]]))


        filtered_state = kalman_filter.kf.x
       
        if abs(filtered_state[0] - cur_pos[0]) < 2 and abs(filtered_state[1] - cur_pos[1]) < 4.5:
            cur_pos = [filtered_state[0], filtered_state[1]]


        print(f"Kalman filtered position: {cur_pos}")

        position_plot.set_data([cur_pos[0]], [cur_pos[1]])

        
        # Refresh the plot
        fig.canvas.draw()
        fig.canvas.flush_events()      
        print(cur_pos)




client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

client.connect("127.0.0.1", 1883, 60)

client.loop_forever()
