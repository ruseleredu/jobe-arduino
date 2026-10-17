#ifndef DHT_MOCK_H
#define DHT_MOCK_H
// Mock de DHT.h (Adafruit) para o toolkit jobe-arduino.
// Leituras DETERMINISTICAS: readTemperature()=24.5, readHumidity()=55.0
// (iguais aos defaults do DHT22 no Wokwi), para permitir correcao por stdout.
#include "Arduino.h"

#define DHT11 11
#define DHT21 21
#define DHT22 22
#define AM2301 21

class DHT {
public:
  DHT(int pin, int type, int count = 6) { (void)pin; (void)type; (void)count; }
  void begin(int = 55) {}
  // force=true no DHT real forca nova leitura; aqui e sempre o valor fixo.
  float readTemperature(bool = false, bool = false) { return 24.5f; }
  float readHumidity(bool = false) { return 55.0f; }
  float computeHeatIndex(float t, float h, bool = true) { (void)h; return t; }
};
#endif
