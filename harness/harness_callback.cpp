// le um comando do stdin, injeta via mock e imprime o estado do LED (pino 2)
WiFiClient _c; PubSubClient _mqtt(_c);
int main() {
  char cmd[64];
  if (scanf("%63s", cmd) != 1) return 1;
  _mqtt.setCallback(aoReceber);
  _mqtt.mock_inject("elt85b/grupo-a/comando", cmd);
  printf("%d\n", mock_pin(2));
  return 0;
}
