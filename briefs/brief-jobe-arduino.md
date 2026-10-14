# Brief — Testar Arduino/PlatformIO no Jobe (sem Moodle)

Resumo denso para reusar em prompts. Objetivo: **avaliar lógica pura** de código
estilo Arduino executando no **Jobe** (sandbox g++), sem hardware, rede nem Moodle.

## Fronteira (o que dá e o que não dá)
- ✅ **Lógica pura**: bits, operadores, controle, tipos, funções, montagem de payload, callbacks MQTT.
- ❌ **Firmware real**: WiFi, GPIO físico, timing, I2C/SPI, broker de verdade → `pio run` (compila p/ ESP32) + **Wokwi**/ESP32 físico.
- Ideia central: trocar `Arduino.h`/libs reais por **mocks** em C++ puro; comparar `stdout`.

## Jobe (API REST — tudo sob `/jobe/index.php/restapi/`)
- `GET  /languages` → lista `[id, versao]` (ex.: `c`, `cpp`, `python3`).
- `POST /runs` → corpo `{"run_spec":{"language_id":"cpp","sourcecode":"...","input":"stdin"}}`.
- `PUT/GET/HEAD /files/{id}` → arquivos de apoio (`{"file_contents":"<base64>"}`, id = MD5). Só um `sourcecode` é compilado.
- Header `X-API-KEY` se exigido. Modo imediato (resultado volta no POST; `GET /runs/{id}` = 404).
- Resposta: `{outcome, cmpinfo, stdout, stderr, run_id}`.
- **outcome**: `15`=OK · `11`=erro compilação (ver `cmpinfo`) · `12`=runtime · `13`=tempo · `17`=memória · `19`=syscall proibida · `20`=interno · `21`=sobrecarga.
- Subir rápido: `docker run -d -p 4000:80 trampgeek/jobeinabox:latest`.

## Receita
1. Mock de `Arduino.h` (+ `WiFi.h`, `PubSubClient.h`) em C++ puro.
2. Montar **UM** fonte = mocks (na ordem) + código do aluno **sem** os `#include` dos mocks + harness.
3. `POST /runs` (`language_id:"cpp"`, `input`=stdin do caso).
4. Passou se `outcome==15` **e** `stdout==esperado`. `11` → mostra `cmpinfo`.
5. Caso de teste = `{"input": "...", "expected": "...\n"}`; harness lê stdin, imprime resultado.

## Mocks (o que implementar)
- **Arduino.h**: `byte`/`boolean`; constantes `HIGH/LOW/INPUT_PULLUP/OUTPUT/LED_BUILTIN/HEX/BIN/OCT/DEC`; macros `bit/bitRead/bitSet/bitClear/bitWrite/highByte/lowByte`; `pinMode` no-op; `digitalWrite`→grava estado (`mock_pin(pin)`); `digitalRead`→valor injetável (`mock_setDigitalRead`); `millis` (contador falso), `delay` no-op; classe **`String`** (`+`, `+=`, `==`, `c_str`, `length`, `toInt`, `toUpperCase`, `indexOf`); **`Serial`**→`stdout` (`print/println` p/ int/HEX/BIN/double/`String`).
- **WiFi.h**: `WL_CONNECTED`, `WIFI_STA`, `struct Client{}`, `struct WiFiClient:Client{}`, objeto `WiFi` (`mode/begin/status`=WL_CONNECTED`/localIP/RSSI/macAddress`).
- **PubSubClient.h**: API real (`setServer/setCallback/connect` [incl. Last Will]/`connected/state/publish/subscribe/loop/disconnect`) que **registra** em vez de conectar. Helpers de teste: `mock_inject(topico,payload)` (dispara o callback), `mock_lastPayload(t)`, `mock_publishedTo(t)`, `mock_subscribedTo(t)`, `mock_publishCount()`.

## Harnesses
- **Função pura** (nível A): lê args do stdin, chama a função, imprime. Ex.: `ehPar`, `somaDigitos`.
- **Sketch** (nível B): mock provê `int main(){ setup(); /* opc: loop() Nx */ }`; captura `Serial`.
- **MQTT payload**: imprime `montaPayload(n,temp)` → compara JSON (`{"n":1,"temp":26.00}`).
- **MQTT callback**: `mock_inject("...","on")` e imprime `mock_pin(LED)` (on→1, off→0).

## Driver `jobe_test.py` (stdlib urllib)
- Args: `--mock` (repetível) `--student` `--harness` `--tests` e `--jobe URL` **ou** `--local` (usa g++; mesmo resultado do Jobe, para dev offline). `--apikey` opcional.
- Remove `#include` dos mocks do código do aluno; combina tudo; roda cada caso; compara `stdout` (tolerante a espaço no fim); imprime OK/diferença/erro-de-compilação; exit 0 só se todos passam (pronto p/ CI).

## Boas práticas / limites
- Peça **funções testáveis** (`montaPayload`, `aoReceber` separados), não lógica embutida no `loop()`.
- Mock cobre lógica e saída serial; **não** simula hardware/rede/timing.
- Tamanho de tipos: host é 64 bits; se o teste depende do ESP32 (int=32 bits), fixe `int32_t`/`uint8_t`.
- Adicione ao mock só o que os exercícios usam.

## Integração com o autograder do curso
- Novo tipo de check `jobe` no `grade.py`: `{"tipo":"jobe","arquivo":"src/main.cpp","harness":"...","casos":[{input,expected}],"desc":"..."}` → monta fonte + roda no Jobe + confere saída. Avalia **comportamento**, sem instalar compiladores no runner de CI.
- Convive com os checks existentes (`contem`/`nao_contem`/`compila`/`release`) e com o modelo de commit `Tn:` avaliado por commit.

## Onde cada coisa roda (mapa)
| Camada | Ferramenta |
|---|---|
| Lógica pura (C/C++/MQTT-logic) | **Jobe** (mock + harness) |
| Compila p/ ESP32 | `pio run` (check `compila`) |
| Firmware em execução | **Wokwi** / ESP32 físico |
| Broker/telemetria real | stack Docker (Mosquitto + Node-RED + MQTT Explorer) |
| Entrega versionada | GitHub + `CommitPoint` (commit `Tn:`) |
