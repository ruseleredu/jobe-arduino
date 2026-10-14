# jobe-arduino

Testar **lógica pura** de código estilo Arduino/PlatformIO no sandbox **Jobe**,
sem hardware, sem rede e sem Moodle. O código do aluno compila contra **mocks**
(`Arduino.h`, `WiFi.h`, `PubSubClient.h`) e a avaliação compara o `stdout`.

> Fronteira: isto testa lógica (bits, operadores, controle, tipos, montagem de
> payload, callbacks MQTT). **Firmware real** (WiFi, GPIO, timing, broker de
> verdade) → `pio run` + **Wokwi**/ESP32 físico.

## Pré-requisitos
- **Docker** (único requisito — não precisa de g++ na máquina).
- **Python 3** (só a biblioteca padrão; nenhuma dependência a instalar).

## 1) Suba o Jobe

```bash
docker compose up -d          # usa o docker-compose.yml deste repo
# confira (deve listar as linguagens, incluindo "cpp"):
curl http://localhost:4000/jobe/index.php/restapi/languages
```

Alternativa sem compose:
```bash
docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest
# depois: docker start jobe / docker stop jobe
```

## 2) Rode um teste

`--jobe` tem default `http://localhost:4000`, então pode ser omitido.

**Exemplo mínimo (Serial.println):**
```bash
python jobe_test.py \
  --mock arduino-mock/Arduino.h \
  --student exemplos/hello_sol.cpp \
  --harness harness/driver_sketch.cpp \
  --tests exemplos/hello_tests.json
```

**Função pura (lê stdin):**
```bash
python jobe_test.py \
  --mock arduino-mock/Arduino.h \
  --student sol.cpp \
  --harness harness/harness_funcao.cpp \
  --tests tests.json
```

**MQTT (vários mocks — repita `--mock`):**
```bash
python jobe_test.py \
  --mock arduino-mock/Arduino.h --mock arduino-mock/WiFi.h --mock arduino-mock/PubSubClient.h \
  --student exemplos/callback_sol.cpp \
  --harness harness/harness_callback.cpp \
  --tests exemplos/callback_tests.json
```

Jobe em outro host/porta ou com chave: `--jobe http://IP:4000 --apikey SUA-CHAVE`.

## Como funciona
O `jobe_test.py` junta **mock(s) + código do aluno (sem os `#include` dos mocks) +
harness** num único `.cpp`, envia ao Jobe (`POST .../restapi/runs`) e compara o
`stdout` com o `expected` de cada caso.

Três desfechos:
- **OK** → compilou, rodou e a saída bateu.
- **SAIDA DIFERENTE** → rodou, mas o texto não confere (mostra esperado × obtido).
- **ERRO DE COMPILACAO** → nem compilou (mostra a mensagem do compilador = `cmpinfo`, outcome 11 do Jobe).

Código de saída `0` só quando **todos** os casos passam (pronto para CI).

## Estrutura
```
jobe-arduino/
├── docker-compose.yml          # sobe o Jobe em :4000
├── jobe_test.py                # driver (só-Jobe; sem modo local)
├── arduino-mock/
│   ├── Arduino.h               # bit macros, String, Serial->stdout, pinos, millis...
│   ├── WiFi.h                  # WiFiClient + objeto WiFi
│   └── PubSubClient.h          # mock MQTT: registra publish/subscribe, injeta mensagens
├── harness/
│   ├── driver_sketch.cpp       # chama setup() uma vez (sketch)
│   ├── harness_funcao.cpp      # chama uma função lendo o stdin
│   ├── harness_payload.cpp     # imprime o payload montado pelo aluno
│   └── harness_callback.cpp    # injeta um comando e imprime o estado do LED
├── exemplos/                   # soluções + *_tests.json (hello, payload, callback)
├── sol.cpp / tests.json        # exemplo de função
```

## tests.json
```json
[
  { "input": "4\n", "expected": "1\n" },
  { "input": "7\n", "expected": "0\n" }
]
```
`input` = stdin do caso · `expected` = stdout esperado (comparação tolerante a
espaços no fim das linhas).

## Limites do mock
Não simula hardware/rede/timing: `digitalRead` é injetável, `millis()` é um
contador falso, `delay()` não espera, `publish`/`subscribe` apenas registram.
Serve para lógica e saída serial. Tipos: o host do Jobe é 64 bits — se o teste
depende do tamanho do ESP32, use `int32_t`/`uint8_t` explícitos.
