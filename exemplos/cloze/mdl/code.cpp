#include <Arduino.h>

void printBin(uint8_t v) { for (int i = 7; i >= 0; i--) Serial.print(bitRead(v, i)); Serial.println(); }

void setup() {
  Serial.begin(115200);
  uint8_t reg = 0b10110010, mask = 0b00001111;
  printBin(reg ^ mask);
}

void loop() {}
