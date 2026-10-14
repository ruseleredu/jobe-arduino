#ifndef PUBSUBCLIENT_MOCK_H
#define PUBSUBCLIENT_MOCK_H
#include "Arduino.h"
#include "WiFi.h"
#include <vector>
#include <string>

// mesma assinatura do callback do PubSubClient real
typedef void (*MQTT_CALLBACK)(char* topic, uint8_t* payload, unsigned int length);

struct PublishRecord { std::string topic; std::string payload; bool retained; };

class PubSubClient {
public:
  PubSubClient() {}
  PubSubClient(Client&) {}

  PubSubClient& setServer(const char* h, uint16_t p){ _host = h?h:""; _port=p; return *this; }
  PubSubClient& setCallback(MQTT_CALLBACK cb){ _cb = cb; return *this; }
  bool setBufferSize(uint16_t){ return true; }

  // connect (varias assinaturas, incl. Last Will)
  boolean connect(const char* id){ _connected=true; _clientId=id?id:""; return true; }
  boolean connect(const char* id, const char*, const char*){ return connect(id); }
  boolean connect(const char* id, const char*, const char*,
                  const char* willTopic, uint8_t, boolean willRetain, const char* willMsg){
    _will = { willTopic?willTopic:"", willMsg?willMsg:"", (bool)willRetain }; return connect(id);
  }

  boolean connected(){ return _connected; }
  void    disconnect(){ _connected=false; }
  int     state(){ return _connected ? 0 : -1; }   // 0 = MQTT_CONNECTED

  boolean publish(const char* t, const char* p){ return publish(t,p,false); }
  boolean publish(const char* t, const char* p, boolean retained){
    published.push_back({ t?t:"", p?p:"", (bool)retained }); return true;
  }

  boolean subscribe(const char* t){ subscribed.push_back(t?t:""); return true; }
  boolean subscribe(const char* t, uint8_t){ return subscribe(t); }
  boolean unsubscribe(const char*){ return true; }
  boolean loop(){ return _connected; }

  // ===== helpers de TESTE (nao existem no PubSubClient real) =====
  // injeta uma mensagem recebida -> dispara o callback do aluno
  void mock_inject(const char* topic, const char* payload){
    if(_cb) _cb((char*)topic, (uint8_t*)payload, (unsigned int)strlen(payload));
  }
  bool mock_publishedTo(const std::string& t) const {
    for(const auto& r : published) {
      if(r.topic==t) return true;
    }
    return false;
  }
  std::string mock_lastPayload(const std::string& t) const {
    for(auto it=published.rbegin(); it!=published.rend(); ++it) {
      if(it->topic==t) return it->payload;
    }
    return "";
  }
  bool mock_subscribedTo(const std::string& t) const {
    for(const auto& s : subscribed) {
      if(s==t) return true;
    }
    return false;
  }
  int mock_publishCount() const { return (int)published.size(); }

  std::vector<PublishRecord> published;
  std::vector<std::string>   subscribed;
  struct { std::string topic, msg; bool retain; } _will;
private:
  MQTT_CALLBACK _cb = nullptr;
  bool _connected = false;
  std::string _host, _clientId;
  uint16_t _port = 0;
};
#endif
