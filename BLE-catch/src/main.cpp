#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>

// Эта переменная будет хранить указатель на объект сканера
BLEScan* pBLEScan;

// Это специальный класс-обработчик. Его метод onResult() будет
// АВТОМАТИЧЕСКИ вызываться каждый раз, когда сканер находит новое BLE-устройство.
class MyAdvertisedDeviceCallbacks: public BLEAdvertisedDeviceCallbacks {
    
    // Этот метод - сердце нашего сканера.
    void onResult(BLEAdvertisedDevice advertisedDevice) {
      // Когда устройство найдено, выводим информацию о нем в Serial порт.
      // Это позволит нам увидеть результат на компьютере.
      Serial.print("Found device: ");
      Serial.print(advertisedDevice.getName().c_str()); // Имя устройства (если есть)
      Serial.print(" | Address: ");
      Serial.print(advertisedDevice.getAddress().toString().c_str()); // MAC-адрес устройства
      Serial.print(" | RSSI: ");
      Serial.print(advertisedDevice.getRSSI()); // Сила сигнала! САМОЕ ВАЖНОЕ ДЛЯ НАС.
      Serial.println();
    }
};

void setup() {
  Serial.begin(115200);
  
  Serial.println("Scanning for BLE devices...");

  // 1. Инициализируем BLE-модуль
  BLEDevice::init("");

  // 2. Получаем объект сканера
  pBLEScan = BLEDevice::getScan(); 
  
  // 3. Привязываем наш класс-обработчик к сканеру.
  // Теперь при нахождении устройства будет вызываться наш код в onResult().
  pBLEScan->setAdvertisedDeviceCallbacks(new MyAdvertisedDeviceCallbacks());
  
  // 4. Устанавливаем параметры сканирования.
  // true = активное сканирование. 1000 мс = продолжительность сканирования.
  pBLEScan->setActiveScan(true); 
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99);
}

void loop() {
  // В основном цикле мы просто запускаем сканирование и ждем результатов.
  Serial.println("Starting new scan cycle...");
  
  // Запускаем сканирование на 5 секунд.
  // В течение этих 5 секунд будет работать наш обработчик onResult()
  BLEScanResults foundDevices = pBLEScan->start(5, false);
  
  Serial.print("Scan finished. Devices found: ");
  Serial.println(foundDevices.getCount());
  
  // Очищаем результаты, чтобы не засорять память
  pBLEScan->clearResults(); 
  
  delay(2000); // Небольшая пауза перед следующим циклом сканирования
}