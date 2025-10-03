# main.py
import bluetooth
import time
import ubinascii
import json

ble = bluetooth.BLE()
ble.active(True)

# IRQ constants (улучшает читаемость)
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

gatt_state = {
    "conn_handle": None,
    "target_char_handle": None,
    "target_addr": None,
    "target_addr_type": None,
}

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
        if ad_type == 0x09:
            try:
                name = data.decode("utf-8")
            except:
                name = data.decode("latin-1", "replace")
        elif ad_type == 0x08:
            try:
                shortened = data.decode("utf-8")
            except:
                shortened = data.decode("latin-1", "replace")
        i += 1 + length
    return name or shortened

def start_gatt_read_device_name(addr_type, addr_bytes):
    if gatt_state["conn_handle"] is not None:
        return
    gatt_state["target_addr"] = bytes(addr_bytes)
    gatt_state["target_addr_type"] = addr_type
    try:
        ble.gap_connect(addr_type, addr_bytes)
    except Exception as e:
        print("gap_connect failed:", e)

def scan_callback(event, data):
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr_bytes, adv_type, rssi, adv_data_bytes = data

        mac = ubinascii.hexlify(addr_bytes, ':').decode().upper()
        raw_adv = ubinascii.hexlify(adv_data_bytes).decode()

        adv_name = decode_adv_name(adv_data_bytes)

        device_info = {
            "mac": mac,
            "rssi": rssi,
            "raw_adv_data": raw_adv,
            "addr_type": addr_type,
            "adv_type": adv_type,
            "adv_name": adv_name
        }
        print(json.dumps(device_info))

        if not adv_name:
            if rssi is not None and rssi > -70:
                start_gatt_read_device_name(addr_type, addr_bytes)

    elif event == _IRQ_SCAN_DONE:
        print("Scan finished")

# обработка GATT/connection событий
def gatt_callback(event, data):
    if event == _IRQ_PERIPHERAL_CONNECT:
        conn_handle, addr_type, addr = data
        print("Connected, conn_handle:", conn_handle)
        gatt_state["conn_handle"] = conn_handle
        try:
            ble.gattc_discover_services(conn_handle)
        except Exception as e:
            print("gattc_discover_services failed:", e)

    elif event == _IRQ_PERIPHERAL_DISCONNECT:
        conn_handle, addr_type, addr = data
        print("Disconnected, conn_handle:", conn_handle)
        gatt_state["conn_handle"] = None
        gatt_state["target_char_handle"] = None
        gatt_state["target_addr"] = None

    elif event == _IRQ_GATTC_SERVICE_RESULT:
        conn_handle, start_handle, end_handle, uuid = data
        try:
            u = bytes(uuid)
        except Exception:
            u = uuid
        if (isinstance(u, (bytes, bytearray)) and len(u) == 2 and u == b'\x00\x18') or (isinstance(u, int) and u == 0x1800):
            try:
                ble.gattc_discover_characteristics(conn_handle, start_handle, end_handle)
            except Exception as e:
                print("gattc_discover_characteristics failed:", e)

    elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
        # data: (conn_handle, def_handle, value_handle, properties, uuid)
        conn_handle, def_handle, value_handle, properties, uuid = data
        try:
            u = bytes(uuid)
        except Exception:
            u = uuid
        # Characteristic 0x2A00 (Device Name)
        if (isinstance(u, (bytes, bytearray)) and len(u) == 2 and u == b'\x00\x2A') or (isinstance(u, int) and u == 0x2A00):
            print("Found Device Name characteristic, value_handle:", value_handle)
            gatt_state["target_char_handle"] = value_handle

    elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
        conn_handle, status = data
        if gatt_state.get("target_char_handle") is not None:
            try:
                ble.gattc_read(conn_handle, gatt_state["target_char_handle"])
            except Exception as e:
                print("gattc_read failed:", e)
        else:
            try:
                ble.gap_disconnect(conn_handle)
            except Exception:
                pass

    elif event == _IRQ_GATTC_READ_RESULT:
        conn_handle, value_handle, char_data = data
        try:
            name = char_data.decode("utf-8")
        except:
            name = char_data.decode("latin-1", "replace")
        print("GATT device name read:", name)
        info = {
            "gatt_name": name,
            "conn_handle": conn_handle
        }
        print(json.dumps(info))
        try:
            ble.gap_disconnect(conn_handle)
        except Exception:
            pass

    elif event == _IRQ_GATTC_READ_DONE:
        pass

def combined_irq(event, data):
    scan_callback(event, data)
    gatt_callback(event, data)

ble.irq(combined_irq)

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

