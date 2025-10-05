# main.py
import bluetooth
import time
import ubinascii
import json
import network
from umqtt.simple import MQTTClient
from machine import Pin, reset
import neopixel
import _thread
import math

# --- Settings ---
WIFI_SSID = "B18104"
WIFI_PASS = "123789qwas"
MQTT_BROKER = "10.31.74.38" 
MQTT_TOPIC = b"ble_rssi/rssi" 
TARGET_NAMES = ["beacon_1", "beacon_2", "beacon_3", "beacon_4", "beacon_5", "beacon_6", "beacon_7", "beacon_8"]
MIN_RSSI = -110

NEOPIXEL_PIN = 48
COLOR_GREEN = (0, 15, 0); COLOR_RED = (15, 0, 0); COLOR_BLUE = (0, 0, 15); COLOR_YELLOW = (15, 15, 0); COLOR_OFF = (0, 0, 0)

SEND_INTERVAL_MS = 1500
HEALTH_CHECK_INTERVAL_MS = 15000


def calculate_stats(data_list):
    if not data_list:
        return None
    
    n = len(data_list)
    
    mean = sum(data_list) / n
    
    variance = sum([(x - mean) ** 2 for x in data_list]) / n
    
    std_dev = math.sqrt(variance)
    
    data_list.sort()
    median = data_list[n // 2]

    max_rssi = max(data_list)
    
    return {
        "avg": round(mean, 2),
        "median": median,
        "std_dev": round(std_dev, 2),
        "samples": n,
        "max_rssi": max_rssi
    }


class BLEScanner:
    def __init__(self, target_names, min_rssi):
        self.target_names = target_names
        self.min_rssi = min_rssi
        self.ble = bluetooth.BLE()
        self.mqtt_client = None
        self.sta_if = network.WLAN(network.STA_IF)
        self.beacons_buffer = {}
        self.np = neopixel.NeoPixel(Pin(NEOPIXEL_PIN), 1)
        self._set_led_color(COLOR_OFF)

    def _set_led_color(self, color): self.np[0] = color; self.np.write()
    def _set_led_status(self): self._set_led_color(COLOR_GREEN if self.sta_if.isconnected() and self.mqtt_client else COLOR_RED)
    def _pulse_led(self, color, duration_ms=20): self._set_led_color(color); time.sleep_ms(duration_ms); self._set_led_status()

    def _connect_wifi(self):
        if self.sta_if.isconnected(): return
        print('Connecting to Wi-Fi...')
        self.sta_if.active(True); self.sta_if.connect(WIFI_SSID, WIFI_PASS)
        while not self.sta_if.isconnected(): self._pulse_led(COLOR_YELLOW, 200); time.sleep_ms(200)
        print('Wi-Fi Connected.')


    def _blinker_thread(self):
        while self.is_connecting:
            self._set_led_color(COLOR_YELLOW)
            time.sleep_ms(500)
            self._set_led_status()
            time.sleep_ms(500)

    def _connect_mqtt(self):
        self.is_connecting = True
        _thread.start_new_thread(self._blinker_thread, ())
        
        try:
            self.mqtt_client = MQTTClient(client_id="", server=MQTT_BROKER, keepalive=60)
            print("Connecting to MQTT broker...")
            self.mqtt_client.connect() 
            print("Connected to MQTT broker.")
        except Exception as e:
            print(f"MQTT connect error: {e}")
            self.mqtt_client = None
        finally:

            self.is_connecting = False
            time.sleep_ms(250) 
            self._set_led_status() 

    def _decode_adv_payload(self, payload_bytes):
        i=0; result={};
        while i < len(payload_bytes):
            l=payload_bytes[i];
            if l==0: break
            t=payload_bytes[i+1]; d=payload_bytes[i+2:i+l+1]
            if t==9 or t==8:
                try: result['name']=bytes(d).decode('utf-8')
                except: pass
            i+=l+1
        return result

    def _scan_callback(self, event, data):
        if event == 5:
            addr_type, addr_bytes, adv_type, rssi, adv_data_bytes = data
            if rssi < self.min_rssi: return
            adv_info = self._decode_adv_payload(adv_data_bytes)
            if 'name' not in adv_info or adv_info['name'] not in self.target_names: return
            device_name = adv_info['name']

            self.beacons_buffer.setdefault(device_name, []).append(rssi)
    def run(self):
        self._connect_wifi(); self._connect_mqtt()
        self.ble.active(True); self.ble.irq(self._scan_callback)
        self.ble.gap_scan(0, 150000, 130000, True)
        # print("Scanner is running...")
        
        last_send_time = time.ticks_ms()
        last_health_check_time = time.ticks_ms()
        
        try:
            while True:
                now = time.ticks_ms()

                # --- SEND DATA ---
                if time.ticks_diff(now, last_send_time) > SEND_INTERVAL_MS:
                    last_send_time = now

                    if self.beacons_buffer and self.mqtt_client:
                        batch_payload = []

                        for name, data in self.beacons_buffer.items():
                            if not data: continue
                            # Send averaged RSSI values
                            stats = calculate_stats(data)
                            if not stats: continue
                            item = {"name": name, 
                                #  "rssi": sum(data) / len(data), 
                                'rssi': stats["median"],
                                'rssi_avg' : stats["avg"],
                                'rssi_std' : stats["std_dev"],
                                'count': stats["samples"],
                                'mrssi': stats["max_rssi"]
                            }

                            batch_payload.append(item)

                        batch_timestamp = {"pack": batch_payload, "timestamp": time.time()}

                        
                        try:
                            payload_str = json.dumps(batch_timestamp)
                            self.mqtt_client.publish(MQTT_TOPIC, payload_str)

                            print(f"Published: {payload_str}")

                            self._pulse_led(COLOR_BLUE)

                            self.beacons_buffer.clear() # Clear buffer
                        except Exception as e:

                            print(f"MQTT publish error: {e}. Data will be resent.")

                            self.mqtt_client = None # Raise flag to reconnect

                            self._set_led_status() # Update LED status

                # --- Network Health Check ---
                if time.ticks_diff(now, last_health_check_time) > HEALTH_CHECK_INTERVAL_MS:
                    last_health_check_time = now
                    if not self.sta_if.isconnected():
                        self._set_led_status()
                        print("Health Check: Wi-Fi disconnected. Reconnecting...")
                        self._connect_wifi()
                    if not self.mqtt_client:
                        self._set_led_status()
                        print("Health Check: MQTT disconnected. Reconnecting...")
                        self._connect_mqtt()
                
                time.sleep_ms(10)
        
        except Exception as e:
            print(f"FATAL ERROR in main loop: {e}")
            self._set_led_color(COLOR_RED)
            time.sleep(10)
            reset() # Hardware reset on fatal error

# --- Main ---
if __name__ == "__main__":
    time.sleep(3)
    scanner = BLEScanner(target_names=TARGET_NAMES, min_rssi=MIN_RSSI)
    scanner.run()