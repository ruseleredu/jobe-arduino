#include <Arduino.h>
// resposta do aluno: monta o JSON de telemetria
String montaPayload(int n, float temp) {
  return String("{\"n\":") + n + ",\"temp\":" + temp + "}";
}
