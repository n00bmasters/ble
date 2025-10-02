import paho.mqtt.client as mqtt
import numpy as np
from math_mod import DistanceCalc, Kalman
import json
import matplotlib.pyplot as plt

rssi = []
f_rssi = []
calc = None
cur_pos = (0,0)
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
    global rssi
    global calc
    global f_rssi

    points = dict()
    client.subscribe("ble_rssi/rssi")
    with open('../config/standart.beacons', 'r') as fp:
        next(fp)
        for i in fp:
            st, x, y = i.split(';')
            points[int(st[-1])] = tuple(map(float, (x, y)))
        #print(points)
        calc = DistanceCalc(points, [-43, -42, -41, -44, -43, -40, -41, -41])
        rssi = [Kalman() for i in range(len(points))]
        f_rssi = [0 for i in range(len(points))]
        #print(rssi)

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
    global rssi
    global f_rssi
    global cur_pos
    rssis = []
    old = 0
    meow = msg.payload.decode("utf-8")
    js = json.loads(meow)["pack"]
    #print(js)
    #print(meow)
    for i in js:
        #print(i)
        name = i['name']
        rssis.append([int(name[name.find('_')+1:]), float(i["rssi"])])
        #rssis.append([int(name[name.find('_')+1:]), rssi[int(name[name.find('_')+1:]) - 1].apply_kalman_filter(i['rssi'])])

    if len(rssis) < 3:
        print('less than 3 available nodes, fix is not obtained')
    else:
        tmp_pos = calc.get_pos(rssis)
        cur_pos = cur_pos if abs(cur_pos[0] - tmp_pos[0]) > 7 or abs(cur_pos[1] - tmp_pos[1]) > 7 else tmp_pos
        # Update only the current position dot
        position_plot.set_data([cur_pos[0]], [cur_pos[1]])
        
        # Refresh the plot
        fig.canvas.draw()
        fig.canvas.flush_events()      
        print(cur_pos)


    
    # prn
    # if not all(f_rssi):
    #     f_rssi[int(js["name"][-1])-1] = float(rssi[int(js["name"][-1])-1].apply_kalman_filter(int(js["rssi"])))
    #     print(msg.payload)
    # else:
    #     f_rssi[int(js["name"][-1])-1] = float(rssi[int(js["name"][-1])-1].apply_kalman_filter(int(js["rssi"])))
    #     print(calc.get_pos(f_rssi))
    #     print(msg.payload)



client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message

client.connect("127.0.0.1", 1883, 60)
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("Stopping...")
finally:
    plt.ioff()
    plt.show()
