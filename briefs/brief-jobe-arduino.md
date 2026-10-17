# Brief — Testar Arduino/PlatformIO no Jobe (sem Moodle)

Resumo denso para reusar em prompts. Objetivo: **avaliar lógica pura** de código
estilo Arduino (e consultas **SQL**) executando no **Jobe** (sandbox), sem hardware,
rede nem Moodle.

## Fronteira (o que dá e o que não dá)
- ✅ **Lógica pura**: bits, operadores, controle, tipos, funções, montagem de payload,
  callbacks MQTT, parsing, e **SQL** (sqlite3).
- ❌ **Firmware real**: WiFi, GPIO físico, timing, I2C/SPI, broker de verdade → `pio run`
  (compila p/ ESP32) + **Wokwi**/ESP32 físico.
- Ideia central: trocar `Arduino.h`/libs reais por **mocks** em C++ puro; comparar `stdout`.

## Jobe (API REST — tudo sob `/jobe/index.php/restapi/`)
- `GET  /languages` → lista `[id, versao]` (ex.: `c`, `cpp`, `python3`, `sqlite3`).
- `POST /runs` → corpo `{"run_spec":{"language_id":"cpp","sourcecode":"...","input":"stdin"}}`.
- Header `X-API-KEY` se exigido. Modo imediato (resultado volta no POST).
- Resposta: `{outcome, cmpinfo, stdout, stderr, run_id}`.
- **outcome**: `15`=OK · `11`=erro compilação (ver `cmpinfo`) · `12`=runtime · `13`=tempo · `17`=memória · `19`=syscall proibida · `20`=interno · `21`=sobrecarga.
- Subir só o Jobe: `docker run -d -p 4000:80 trampgeek/jobeinabox:latest`. Na **stack do
  curso** (compose) o Jobe escuta a porta **80 na rede interna** (host `4000:80`); dentro
  do container de ferramentas o default é `JOBE_URL=http://jobe`.

## Imagem de ferramentas `esp32-pio-wokwi`
Container com PlatformIO Core, Wokwi CLI, Python+Pygments e o toolkit `jobe-arduino`
embutido (scripts no PATH; mocks e `templates/` em `JOBE_ARDUINO_HOME`). O repo de
questões é montado em `/work`:
```bash
docker compose up -d
docker compose exec esp32-pio-wokwi bash -c "gen_tests.py quiz01/minha_questao"
docker compose exec esp32-pio-wokwi bash -c "jobe_test.py quiz01/minha_questao"
docker compose exec esp32-pio-wokwi bash -c "gen_moodle_xml.py quiz01"
```

## Receita (código Arduino/C++)
1. Mock de `Arduino.h` (+ `WiFi.h`, `PubSubClient.h`, `DHT.h`, `Ticker.h`, `esp32-hal-log.h`).
2. Montar **UM** fonte = mocks (na ordem) + código do aluno **sem** os `#include` dos mocks + harness.
3. `POST /runs` (`language_id:"cpp"`, `input`=stdin do caso).
4. Passou se `outcome==15` **e** `stdout==esperado`. `11` → mostra `cmpinfo`.

## Mocks (`arduino-mock/`)
- **Arduino.h**: `byte`/`boolean`; constantes `HIGH/LOW/INPUT_PULLUP/OUTPUT/LED_BUILTIN/HEX/BIN/OCT/DEC`; macros `bit/bitRead/bitSet/bitClear/bitWrite/highByte/lowByte`; `pinMode` no-op; `digitalWrite`→grava estado; `digitalRead`; `millis`/`delay`; classe **`String`**; **`Serial`**→`stdout`.
- **WiFi.h**: `WL_CONNECTED`, `WIFI_STA`, `WiFiClient`, objeto `WiFi` (`mode/begin/status/localIP/RSSI`).
- **PubSubClient.h**: API real (`setServer/setCallback/connect` [incl. Last Will, 5 e 7 args]/`connected/state/publish/subscribe/loop`) que **registra** em vez de conectar. Helpers: `mock_inject`, `mock_lastPayload`, `mock_publishedTo`, `mock_subscribedTo`, `mock_publishCount`.
- **DHT.h**: `DHT22`; `readTemperature()`=24.5, `readHumidity()`=55.0 (determinístico).
- **Ticker.h**: `attach/attach_ms/once/detach` (no-op; `mock_fire()` dispara o callback nos testes).
- **esp32-hal-log.h**: `log_e/w/i/d/v` → `[E]/[W]/[I]/[D]/[V] msg`, respeitando `CORE_DEBUG_LEVEL`.

## Harnesses (por tipo em `question.json`)
- **`c_function`/`cpp_function`**: `<base>_sol.cpp` define a função; o toolkit acrescenta `main(){ testcode; }` por caso (`cases.txt` → `tests.json`). `call` com `{}` imprime o retorno.
- **`c_program`/`cpp_program`**: o aluno escreve `main`; teste via `stdin`.
- **`arduino`** (sketch): mocks + código + harness `int main(){ setup(); }` (uma execução; saída inteira = esperado). Ideal para "completar o código" `setup()/loop()` (sem `main`).
- **`sql`**: `schema.sql` + consulta (`<base>_sol.sql`) rodados no `sqlite3`; saída em modo list (`|`, sem cabeçalho).

## Driver `jobe_test.py` (stdlib urllib) — **modo pasta** (recomendado)
- `jobe_test.py <pasta>` lê `question.json`, a referência e `tests.json` de `<pasta>/mdl/`
  (aceita também `<pasta>/mdl`), monta o fonte conforme o `type` e roda cada caso no Jobe.
- `--answer entrega.cpp` testa a entrega de um aluno em vez da referência.
- `--jobe URL` (default `http://localhost:4000` ou env `JOBE_URL`), `--apikey` se exigido.
- Compara `stdout` (tolerante a espaço no fim); OK/diferença/erro-de-compilação; exit 0 só se todos passam.
- (Há um **modo flags** legado: `--mock/--student/--harness/--tests` para fontes avulsos.)
- Geração dos esperados: `gen_tests.py <pasta>` roda a **referência** e grava `<base>_tests.json`.

## Boas práticas / limites
- Peça **funções testáveis** (`montaPayload`, `aoReceber` separados), não lógica embutida no `loop()`.
- Mock cobre lógica e saída serial; **não** simula hardware/rede/timing. WiFi/MQTT/log com
  saída variável no hardware → questão **conceitual** (Cloze), não "qual a saída exata".
- Tamanho de tipos: host é 64 bits; se depender do ESP32 (int=32 bits), fixe `int32_t`/`uint8_t`.
- Adicione ao mock só o que os exercícios usam.

## Onde cada coisa roda (mapa)
| Camada | Ferramenta |
|---|---|
| Lógica pura (C/C++/MQTT-logic/SQL) | **Jobe** (mock + harness / sqlite3) |
| Compila p/ ESP32 | `pio run` |
| Firmware em execução | **Wokwi** / ESP32 físico |
| Broker/telemetria real | stack Docker (Mosquitto + Node-RED + MQTT Explorer) |
| Entrega versionada | GitHub + `CommitPoint` (commit `Tn:`) |
