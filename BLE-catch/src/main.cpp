#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>


BLEScan* pBLEScan;


class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
  
    void onResult(BLEAdvertisedDevice advertisedDevice) {
      Serial.print("Found device: ");
      Serial.print(advertisedDevice.getName().c_str());
      Serial.print(" | Address: ");
      Serial.print(advertisedDevice.getAddress().toString().c_str()); 
      Serial.print(" | RSSI: ");
      Serial.print(advertisedDevice.getRSSI());
      Serial.println();
    }
};

void setup() {
  Serial.begin(115200);
  
  Serial.println("Scanning for BLE devices...");

  BLEDevice::init("");

  pBLEScan = BLEDevice::getScan(); 
  
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  
  pBLEScan->setActiveScan(true); 
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
}

void loop() {
  Serial.println("Starting new scan cycle...");

  BLEScanResults foundDevices = pBLEScan->start(5, false);
  
  Serial.print("Scan finished. Devices found: ");
  Serial.println(foundDevices.getCount());
  
  pBLEScan->clearResults(); 
  
}