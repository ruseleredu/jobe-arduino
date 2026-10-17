#ifndef TICKER_MOCK_H
#define TICKER_MOCK_H
// Mock de Ticker.h (core ESP32) para o toolkit jobe-arduino.
// No sandbox (sem event loop) o callback NAO dispara sozinho; attach apenas guarda
// a funcao. Questoes que precisam de saida fazem a acao direto no setup().
// Util para que sketches com Ticker compilem no Jobe.

typedef void (*TickerFn)();

class Ticker {
public:
  void attach(float, TickerFn fn)            { _fn = fn; }
  void attach_ms(unsigned long, TickerFn fn) { _fn = fn; }
  void once(float, TickerFn fn)              { _fn = fn; }
  void once_ms(unsigned long, TickerFn fn)   { _fn = fn; }
  void detach()                              { _fn = nullptr; }
  bool active() const                        { return _fn != nullptr; }
  // helper de TESTE (nao existe no Ticker real): dispara o callback manualmente
  void mock_fire()                           { if (_fn) _fn(); }
private:
  TickerFn _fn = nullptr;
};
#endif
