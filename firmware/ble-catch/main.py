# main.py
"""
Скан BLE-устройств фильтрация по имени и RSSI
возврат json
"""
import bluetooth
import time
import ubinascii
import json
import network






print("Starting up... Press Ctrl+C to enter REPL.")
time.sleep(5) 
ble = bluetooth.BLE()
ble.active(True)

TARGET_NAMES = [
    "beacon_1", 
    "beacon_2", 
    "beacon_3", 
    "beacon_4",
    "beacon_5",
    "beacon_6",
    "beacon_7",
    "beacon_8"
]

MIN_RSSI = -80

def decode_adv_payload(payload_bytes):
    i = 0
    result = {}
    while i < len(payload_bytes):
        length = payload_bytes[i]
        if length == 0:
            break
        
        ad_type = payload_bytes[i + 1]
        data = payload_bytes[i + 2 : i + length + 1]
        
        # 0x09 = Complete Local Name, 0x08 = Shortened Local Name
        if ad_type == 0x09 or ad_type == 0x08:
            try:
                result['name'] = bytes(data).decode('utf-8')
            except UnicodeError:
                result['name'] = 'decoding_error'
        
        i += length + 1
    return result


def scan_callback(event, data):
    # event 5 - это _IRQ_SCAN_RESULT
    if event == 5:
        addr_type, addr_bytes, adv_type, rssi, adv_data_bytes = data
        
        if rssi < MIN_RSSI:
            return
        
    
        adv_info = decode_adv_payload(adv_data_bytes)

        if 'name' not in adv_info or adv_info['name'] not in TARGET_NAMES:
            return
            
        device_name = adv_info['name']

        device_info = {
            "mac": ubinascii.hexlify(addr_bytes, ':').decode().upper(),
            "rssi": rssi,
            "addr_type": addr_type,
            "adv_type": adv_type,
            "name": device_name
        }

        print(json.dumps(device_info))

ble.irq(scan_callback)



# ---  СКАНИРОВАНИЕ ПО ДОКАМ ---
# scan(0, ...) -> сканировать бесконечно
# active=True -> включаем АКТИВНОЕ сканирование
print("Starting explorer mode... Showing ALL found devices.")
ble.gap_scan(0, 150000, 130000, True)


try:
    while True:
        time.sleep_ms(100)
except KeyboardInterrupt:
    ble.gap_scan(None)
    print("Scanner stopped.")