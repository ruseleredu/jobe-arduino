#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  Serial.println("Ola, Jobe!");       // linha 1 (texto)
  Serial.print("2 + 3 = ");
  Serial.println(2 + 3);              // linha 2 (numero)
}

void loop() {}
