# main_beacon_test.py
import bluetooth
import time

ble = bluetooth.BLE()
ble.active(True)

# Рекламный пакет с именем устройства
payload = b'\x02\x01\x06\x09\x09MyESP32S3'

print("Starting BLE beacon...")

while True:
    ble.gap_advertise(100000, adv_data=payload)
    print("Advertising...")
    time.sleep(2)
    ble.gap_advertise(None) 
    time.sleep(2)