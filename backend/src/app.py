from fastapi import FastAPI
import paho.mqtt.client as mqtt

def on_connect(client, userdata, message):
    client.subscribe("ble_rssi/#")

def on_message(client, userdata, msg):
    

client = mqtt.Client(client, userdata, msg)

