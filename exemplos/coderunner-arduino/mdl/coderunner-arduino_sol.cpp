#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  for (int i = 1; i <= 3; i++) { Serial.print("ciclo "); Serial.println(i); }
}

void loop() {}
