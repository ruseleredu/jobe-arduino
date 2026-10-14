#ifndef ESP32_HAL_LOG_MOCK_H
#define ESP32_HAL_LOG_MOCK_H
// Mock de esp32-hal-log.h para o toolkit jobe-arduino.
// Saida DETERMINISTICA (sem timestamp/arquivo/linha), no formato "[<nivel>] <msg>\n",
// para permitir correcao automatica por comparacao de stdout.
#include <cstdio>

// Niveis (iguais ao core Arduino-ESP32)
#define ARDUHAL_LOG_LEVEL_NONE    0
#define ARDUHAL_LOG_LEVEL_ERROR   1
#define ARDUHAL_LOG_LEVEL_WARN    2
#define ARDUHAL_LOG_LEVEL_INFO    3
#define ARDUHAL_LOG_LEVEL_DEBUG   4
#define ARDUHAL_LOG_LEVEL_VERBOSE 5

// Nivel de compilacao. No PlatformIO vem de build_flags (-DCORE_DEBUG_LEVEL=n).
// Aqui: sobrescrevivel (defina antes de incluir, ou via "defines" no question.json).
// Default = VERBOSE (mostra todos os logs).
#ifndef CORE_DEBUG_LEVEL
#define CORE_DEBUG_LEVEL ARDUHAL_LOG_LEVEL_VERBOSE
#endif

// Cada macro so imprime se CORE_DEBUG_LEVEL for >= ao seu nivel (filtragem em
// tempo de compilacao, como no ESP32 real). fmt deve ser string literal.
#define log_e(fmt, ...) do { if (CORE_DEBUG_LEVEL >= ARDUHAL_LOG_LEVEL_ERROR)   printf("[E] " fmt "\n", ##__VA_ARGS__); } while (0)
#define log_w(fmt, ...) do { if (CORE_DEBUG_LEVEL >= ARDUHAL_LOG_LEVEL_WARN)    printf("[W] " fmt "\n", ##__VA_ARGS__); } while (0)
#define log_i(fmt, ...) do { if (CORE_DEBUG_LEVEL >= ARDUHAL_LOG_LEVEL_INFO)    printf("[I] " fmt "\n", ##__VA_ARGS__); } while (0)
#define log_d(fmt, ...) do { if (CORE_DEBUG_LEVEL >= ARDUHAL_LOG_LEVEL_DEBUG)   printf("[D] " fmt "\n", ##__VA_ARGS__); } while (0)
#define log_v(fmt, ...) do { if (CORE_DEBUG_LEVEL >= ARDUHAL_LOG_LEVEL_VERBOSE) printf("[V] " fmt "\n", ##__VA_ARGS__); } while (0)

#endif
