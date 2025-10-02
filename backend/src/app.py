import paho.mqtt.client as mqtt
import numpy as np
from math_mod import DistanceCalc, Kalman
import json

rssi = []
f_rssi = []
calc = None
#points = {}

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
        print(points)
        calc = DistanceCalc(points, [-50 for i in range(len(points))])
        rssi = [Kalman() for i in range(len(points))]
        f_rssi = [0 for i in range(len(points))]
        #print(rssi)

def on_message(client, userdata, msg):
    global rssi
    global f_rssi
    nodes_available = []
    rssis = []
    old = 0
    meow = msg.payload.decode("utf-8")
    js = json.loads(meow)["pack"]
    print(js)
    print(meow)
    for i in js:
        print(i)
        name = i['name']
        nodes_available.append(int(name[name.find('_')+1:]))
        #print(int(name[name.find('_')+1:]))
        rssis.append(rssi[int(name[name.find('_')+1:]) - 1].apply_kalman_filter(i['rssi']))

    if len(nodes_available) < 3:
        print('less than 3 available nodes, fix is not obtained')
    else:
        print(calc.get_pos(nodes_available, rssis))


    
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
client.loop_forever()
