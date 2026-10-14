#include <WiFi.h>
#include <PubSubClient.h>
const int LED = 2;
// resposta do aluno: liga/desliga o LED conforme a mensagem
void aoReceber(char* topico, byte* payload, unsigned int tam) {
  String msg;
  for (unsigned int i = 0; i < tam; i++) msg += (char)payload[i];
  if (msg == "on")  digitalWrite(LED, HIGH);
  if (msg == "off") digitalWrite(LED, LOW);
}
