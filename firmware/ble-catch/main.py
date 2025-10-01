# main.py
import bluetooth
import time
import ubinascii
import json

ble = bluetooth.BLE()
ble.active(True)


def scan_callback(event, data):
    # event 5 - это _IRQ_SCAN_RESULT
    if event == 5:
        addr_type, addr_bytes, adv_type, rssi, adv_data_bytes = data
        
        device_info = {
            "mac": ubinascii.hexlify(addr_bytes, ':').decode().upper(),
            "rssi": rssi,
            "raw_adv_data": ubinascii.hexlify(adv_data_bytes).decode(),
            "addr_type": addr_type,
            "adv_type": adv_type
        }
        print(json.dumps(device_info))

ble.irq(scan_callback)

print("Starting ACTIVE ASYNC scanner...")

# ---  СКАНИРОВАНИЕ ПО ДОКАМ ---
# scan(0, ...) -> сканировать бесконечно
# active=True -> включаем АКТИВНОЕ сканирование
ble.gap_scan(0, 150000, 130000, True)


try:
    while True:
        time.sleep_ms(100)
except KeyboardInterrupt:
    ble.gap_scan(None)
    print("Scanner stopped.")