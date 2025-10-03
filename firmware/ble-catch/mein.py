# main.py
import bluetooth
import time
import ubinascii
import json

ble = bluetooth.BLE()
ble.active(True)

# MicroPython ubluetooth IRQ numbers (for readability)
_IRQ_SCAN_RESULT = 5
_IRQ_SCAN_DONE = 6
_IRQ_PERIPHERAL_CONNECT = 7
_IRQ_PERIPHERAL_DISCONNECT = 8
_IRQ_GATTC_SERVICE_RESULT = 9
_IRQ_GATTC_SERVICE_DONE = 10
_IRQ_GATTC_CHARACTERISTIC_RESULT = 11
_IRQ_GATTC_CHARACTERISTIC_DONE = 12
_IRQ_GATTC_READ_RESULT = 15
_IRQ_GATTC_READ_DONE = 16

def decode_adv_name(adv_bytes):
    i = 0
    name = None
    shortened = None
    while i < len(adv_bytes):
        length = adv_bytes[i]
        if length == 0:
            break
        ad_type = adv_bytes[i + 1]
        data = adv_bytes[i + 2 : i + 1 + length]
        # 0x09 = Complete Local Name, 0x08 = Shortened Local Name
        if ad_type == 0x09:
            try:
                name = data.decode('utf-8')
            except:
                name = data.decode('latin-1', 'replace')
            # prefer complete name, we can break but we'll still scan to end
        elif ad_type == 0x08:
            try:
                shortened = data.decode('utf-8')
            except:
                shortened = data.decode('latin-1', 'replace')
        i += 1 + length
    return name or shortened

# state for GATT client flow (simple single-connection example)
gatt_state = {
    'conn_handle': None,
    'target_char_handle': None,
    'target_addr': None,
    'target_addr_type': None,
}

def start_gatt_read_device_name(addr_type, addr_bytes):
    print("Connecting to", ubinascii.hexlify(addr_bytes, ':').decode().upper())
    gatt_state['target_addr'] = bytes(addr_bytes)
    gatt_state['target_addr_type'] = addr_type
    try:
        ble.gap_connect(addr_type, addr_bytes)
    except Exception as e:
        print("gap_connect failed:", e)

def scan_callback(event, data):
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr_bytes, adv_type, rssi, adv_data_bytes = data

        mac = ubinascii.hexlify(addr_bytes, ':').decode().upper()
        raw = ubinascii.hexlify(adv_data_bytes).decode()

        name_from_adv = decode_adv_name(adv_data_bytes)
        device_info = {
            "mac": mac,
            "rssi": rssi,
            "raw_adv_data": raw,
            "addr_type": addr_type,
            "adv_type": adv_type,
            "adv_name": name_from_adv
        }

        print(json.dumps(device_info))

        if not name_from_adv:
            if rssi and rssi > -70:
                start_gatt_read_device_name(addr_type, addr_bytes)

    elif event == _IRQ_SCAN_DONE:
        print("Scan finished")


def ble_irq(event, data):
    if event == _IRQ_PERIPHERAL_CONNECT:
        conn_handle, addr_type, addr = data
        print("Connected, conn_handle:", conn_handle)
        gatt_state['conn_handle'] = conn_handle
        try:
            ble.gattc_discover_services(conn_handle)
        except Exception as e:
            print("gattc_discover_services failed:", e)

    elif event == _IRQ_PERIPHERAL_DISCONNECT:
        conn_handle, addr_type, addr = data
        print("Disconnected, conn_handle:", conn_handle)
        gatt_state['conn_handle'] = None
        gatt_state['target_char_handle'] = None
        gatt_state['target_addr'] = None

    elif event == _IRQ_GATTC_SERVICE_RESULT:
        conn_handle, start_handle, end_handle, uuid = data
        try:
            u = bytes(uuid)
        except:
            u = uuid

        if (isinstance(u, (bytes, bytearray)) and len(u) == 2 and u == b'\x00\x18') or (isinstance(u, int) and u == 0x1800):
            print("Found Generic Access service, discovering characteristics")
            ble.gattc_discover_characteristics(conn_handle, start_handle, end_handle)

    elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
        conn_handle, def_handle, value_handle, properties, uuid = data
        try:
            u = bytes(uuid)
        except:
            u = uuid
        # Characteristic UUID 0x2A00 = Device Name
        if (isinstance(u, (bytes, bytearray)) and len(u) == 2 and u == b'\x00\x2A') or (isinstance(u, int) and u == 0x2A00):
            print("Found Device Name characteristic, value_handle:", value_handle)
            gatt_state['target_char_handle'] = value_handle

    elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
        conn_handle, status = data
        if gatt_state.get('target_char_handle') is not None:
            try:
                ble.gattc_read(conn_handle, gatt_state['target_char_handle'])
            except Exception as e:
                print("gattc_read failed:", e)
        else:
            try:
                ble.gap_disconnect(conn_handle)
            except:
                pass

    elif event == _IRQ_GATTC_READ_RESULT:
        conn_handle, value_handle, char_data = data
        try:
            name = char_data.decode('utf-8')
        except:
            name = char_data.decode('latin-1', 'replace')
        print("GATT device name read:", name)
        info = {
            "gatt_name": name,
            "conn_handle": conn_handle
        }
        print(json.dumps(info))
        try:
            ble.gap_disconnect(conn_handle)
        except:
            pass

    elif event == _IRQ_GATTC_READ_DONE:
        pass

ble.irq(scan_callback)   # note: we keep your original scan callback for scan events

def combined_irq(event, data):
    scan_callback(event, data)
    ble_irq(event, data)

ble.irq(combined_irq)

print("Starting ACTIVE ASYNC scanner...")

# start active scan (infinite)
ble.gap_scan(0, 150000, 130000, True)

try:
    while True:
        time.sleep_ms(100)
except KeyboardInterrupt:
    ble.gap_scan(None)
    print("Scanner stopped.")

