# main.py
import bluetooth
import time
import ubinascii
import json


print("BLE scanner started...")

while True:
    try:
        print("\n--- New Scan Cycle ---")

        ble = bluetooth.BLE()
        ble.active(True)
        
        found_devices = ble.gap_scan(8000, 130000, 110000)
        
        if not found_devices:
            print("No devices found.")
        else:
            print(f"Found {len(found_devices)} devices.")
            output_data = []
            for device in found_devices:
                addr_type, addr_bytes, adv_type, rssi, adv_data_bytes = device
                device_info = {
                    "mac": ubinascii.hexlify(addr_bytes, ':').decode().upper(),
                    "rssi": rssi,
                    "raw_adv_data": ubinascii.hexlify(adv_data_bytes).decode(),
                    "addr_type": addr_type,
                    "adv_type": adv_type
                }
                output_data.append(device_info)
            
            print(json.dumps(output_data))

    except OSError as e:

        print(f"An unexpected error occurred: {e}")

    time.sleep(2)