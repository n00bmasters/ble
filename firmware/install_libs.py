# firmware/install_libs.py
import network
import time
import mip

# --- ВАЖНО: Впиши сюда свои данные от Wi-Fi! ---
WIFI_SSID = "YOUR_WIFI_SSID"
WIFI_PASS = "YOUR_WIFI_PASSWORD"

# Список библиотек для установки
PACKAGES = ["micropython-umqtt.simple", "neopixel"]

def connect_wifi():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print(f"Connecting to {WIFI_SSID}...")
        sta_if.active(True)
        sta_if.connect(WIFI_SSID, WIFI_PASS)
        while not sta_if.isconnected():
            print(".")
            time.sleep(1)
    print("WiFi Connected. IP:", sta_if.ifconfig())

def install_packages():
    for package in PACKAGES:
        print(f"\nInstalling {package}...")
        try:
            mip.install(package)
            print(f"Successfully installed {package}.")
        except Exception as e:
            print(f"ERROR: Failed to install {package}. Error: {e}")

# --- Основной скрипт ---
connect_wifi()
install_packages()

print("\n--- Libraries installation complete! ---")
print("You can now delete main.py from the board and upload your final code.")