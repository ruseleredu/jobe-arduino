#ifndef ARDUINO_MOCK_H
#define ARDUINO_MOCK_H
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#include <cctype>
#include <string>

typedef uint8_t byte;
typedef bool boolean;

#define HIGH 1
#define LOW 0
#define INPUT 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define LED_BUILTIN 2
#define DEC 10
#define HEX 16
#define OCT 8
#define BIN 2

#define bit(b) (1UL << (b))
#define bitRead(v,b) (((v) >> (b)) & 0x01)
#define bitSet(v,b) ((v) |= (1UL << (b)))
#define bitClear(v,b) ((v) &= ~(1UL << (b)))
#define bitWrite(v,b,x) ((x) ? bitSet(v,b) : bitClear(v,b))
#define highByte(w) ((uint8_t)((w) >> 8))
#define lowByte(w) ((uint8_t)((w) & 0xff))

// ---- estado de pinos (para os testes) ----
[[maybe_unused]] static int _pinOut[64] = {0};
[[maybe_unused]] static int _pinIn[64];
inline void pinMode(int, int) {}
inline void digitalWrite(int pin, int val){ if(pin>=0 && pin<64) _pinOut[pin]=val; }
inline int  digitalRead(int pin){ return (pin>=0 && pin<64) ? _pinIn[pin] : HIGH; }
inline int  mock_pin(int pin){ return (pin>=0 && pin<64) ? _pinOut[pin] : -1; }        // estado de saida
inline void mock_setDigitalRead(int pin,int v){ if(pin>=0 && pin<64) _pinIn[pin]=v; }   // simula entrada
inline unsigned long millis(){ static unsigned long t=0; return t+=1; }
inline void delay(unsigned long){}

// ---- classe String (subconjunto do Arduino) ----
class String {
  std::string s;
public:
  String() {}
  String(const char* p): s(p ? p : "") {}
  String(const std::string& p): s(p) {}
  String(char c){ s = std::string(1, c); }
  String(int v){ s = std::to_string(v); }
  String(unsigned int v){ s = std::to_string(v); }
  String(long v){ s = std::to_string(v); }
  String(unsigned long v){ s = std::to_string(v); }
  String(double v){ char b[32]; snprintf(b,sizeof(b),"%.2f",v); s=b; }
  String(float v){ char b[32]; snprintf(b,sizeof(b),"%.2f",(double)v); s=b; }
  const char* c_str() const { return s.c_str(); }
  unsigned int length() const { return (unsigned)s.size(); }
  char operator[](int i) const { return s[i]; }
  String operator+(const String& o) const { return String(s + o.s); }
  String& operator+=(const String& o){ s += o.s; return *this; }
  bool operator==(const String& o) const { return s == o.s; }
  bool operator==(const char* p) const { return s == (p ? p : ""); }
  long toInt() const { return atol(s.c_str()); }
  void toUpperCase(){ for(char& c : s) c = (char)toupper((unsigned char)c); }
  void toLowerCase(){ for(char& c : s) c = (char)tolower((unsigned char)c); }
  int indexOf(char c) const { auto p=s.find(c); return p==std::string::npos?-1:(int)p; }
  const std::string& raw() const { return s; }
};
inline String operator+(const char* a, const String& b){ return String(a) + b; }

// ---- Serial -> stdout ----
struct SerialMock {
  void begin(long){}
  void print(const char*s){ fputs(s,stdout); }
  void print(const String& s){ fputs(s.c_str(),stdout); }
  void print(char c){ putchar(c); }
  void print(int v,int base=DEC){ pb((long)v,base); }
  void print(long v,int base=DEC){ pb(v,base); }
  void print(unsigned int v,int base=DEC){ pb((long)v,base); }
  void print(unsigned long v,int base=DEC){ pb((long)v,base); }
  void print(double v){ printf("%.2f",v); }
  void print(double v,int d){ printf("%.*f",d,v); }
  void println(){ putchar('\n'); }
  void println(const char*s){ fputs(s,stdout); putchar('\n'); }
  void println(const String& s){ fputs(s.c_str(),stdout); putchar('\n'); }
  template<class T> void println(T v){ print(v); putchar('\n'); }
  template<class T> void println(T v,int base){ print(v,base); putchar('\n'); }
  int available(){ return 0; }
  int read(){ return -1; }
private:
  void pb(long v,int base){
    if(base==HEX){ printf("%lX",(unsigned long)v); }
    else if(base==OCT){ printf("%lo",(unsigned long)v); }
    else if(base==BIN){ unsigned long u=(unsigned long)v; if(!u){putchar('0');return;} char b[65];int i=0; while(u){b[i++]='0'+(u&1);u>>=1;} while(i--)putchar(b[i]); }
    else printf("%ld",v);
  }
};
[[maybe_unused]] static SerialMock Serial;
#endif
