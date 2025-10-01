# main.py
import bluetooth
import time
import ubinascii
import json
import network
from umqtt.simple import MQTTClient

# --- Main Settings ---
WIFI_SSID = "B18104"
WIFI_PASS = "123789qwas"

MQTT_BROKER = "10.31.74.38" 
MQTT_TOPIC = b"ble_rssi/rssi" 

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

MIN_RSSI = -110

class BLEScanner:
    def __init__(self, target_names, min_rssi):
        self.target_names = target_names
        self.min_rssi = min_rssi
        self.ble = bluetooth.BLE()
        self.mqtt_client = None
        self.beacons_buffer = {}

        self.sta_if = network.WLAN(network.STA_IF)
        
    def _connect_wifi(self):
        if not self.sta_if.isconnected():
            print('Connecting to network...')
            self.sta_if.active(True)
            self.sta_if.connect(WIFI_SSID, WIFI_PASS)
            while not self.sta_if.isconnected():
                time.sleep(1)
        print('Network config:', self.sta_if.ifconfig())

    def _check_wifi(self):
        return self.sta_if.isconnected()

    def _connect_mqtt(self):
        self.mqtt_client = MQTTClient(client_id="", server=MQTT_BROKER)
        print("Connecting to MQTT broker...")
        self.mqtt_client.connect()
        print("Connected to MQTT broker.")

    def _check_mqtt(self): 
        try:
            self.mqtt_client.ping()
            return True
        except:
            return False

    def _decode_adv_payload(self, payload_bytes):
        i = 0
        result = {}
        while i < len(payload_bytes):
            length = payload_bytes[i]
            if length == 0: break
            ad_type = payload_bytes[i + 1]
            data = payload_bytes[i + 2 : i + length + 1]
            if ad_type == 0x09 or ad_type == 0x08:
                try: result['name'] = bytes(data).decode('utf-8')
                except UnicodeError: pass
            i += length + 1
        return result

    def _scan_callback(self, event, data):
        if event == 5:
            addr_type, addr_bytes, adv_type, rssi, adv_data_bytes = data
            if rssi < self.min_rssi: return
            adv_info = self._decode_adv_payload(adv_data_bytes)
            if 'name' not in adv_info or adv_info['name'] not in self.target_names: return

            device_name = adv_info['name']
            if device_name not in self.beacons_buffer or rssi > self.beacons_buffer[device_name]['rssi']:
                self.beacons_buffer[device_name] = {
                    # "mac": ubinascii.hexlify(addr_bytes, ':').decode().upper(),
                    "rssi": rssi,
                    # "last_seen": time.time()
                }

            
            # payload = json.dumps(device_info)
            # print(f"Publishing: {payload}")
            # self.mqtt_client.publish(MQTT_TOPIC, payload)
    
    def run(self):
        self._connect_wifi()
        self._connect_mqtt()
        self.ble.active(True)
        self.ble.irq(self._scan_callback)
        
        print(f"Starting initial scanner...")
        self.ble.gap_scan(0, 150000, 130000, True)
        
        last_check = time.ticks_ms()
        
        while True:
            time.sleep(0.1)
            wifi_ok = self.sta_if.isconnected()
            mqtt_ok = self._check_mqtt()

            if not wifi_ok or not mqtt_ok:
                print("Network issue detected. Pausing scanner for maintenance...")
                self.ble.gap_scan(None) 
                time.sleep_ms(200)

                if not wifi_ok:
                    self._connect_wifi()
                
                if self.sta_if.isconnected() and not mqtt_ok:
                    self._connect_mqtt()

                print("Resuming scanner...")
                self.ble.gap_scan(0, 150000, 130000, True)
            if self.beacons_buffer:
                batch_payload = []
                for name, data in self.beacons_buffer.items():
                    item = {"name": name, "rssi": data["rssi"]}
                    batch_payload.append(item)
                
                try:
                    payload_str = json.dumps(batch_payload)
                    self.mqtt_client.publish(MQTT_TOPIC, payload_str)
                    print(f"Published batch: {payload_str}")
                except Exception as e:
                    print(f"Failed to publish batch: {e}")
                    self.mqtt_client = None # Сбрасываем клиент при ошибке
                
                # Очищаем "корзину" для следующего 5-секундного сбора
                self.beacons_buffer.clear()
            else:
                print("No beacons detected in this interval.")
                


# --- Main ---
if __name__ == "__main__":
    print("BLE Scanner with MQTT")
    scanner = BLEScanner(target_names=TARGET_NAMES, min_rssi=MIN_RSSI)
    scanner.run()