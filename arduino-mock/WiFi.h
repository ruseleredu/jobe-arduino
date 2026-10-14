#ifndef WIFI_MOCK_H
#define WIFI_MOCK_H
#include "Arduino.h"
#define WL_CONNECTED 3
#define WIFI_STA 1
struct Client {};                 // base para clientes de rede
struct WiFiClient : Client {};
struct WiFiMock {
  void mode(int){}
  void begin(const char*, const char* = ""){}
  int  status(){ return WL_CONNECTED; }
  String localIP(){ return String("10.13.37.2"); }
  long RSSI(){ return -30; }
  String macAddress(){ return String("24:0A:C4:00:00:01"); }
};
[[maybe_unused]] static WiFiMock WiFi;
#endif
