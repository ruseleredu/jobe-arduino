# Brief — Pasta de questão CodeRunner (aluno ESCREVE código)

Cole este brief num prompt de IA e preencha o "Pedido". A IA deve devolver os
arquivos de UMA pasta de questão no padrão do toolkit `jobe-arduino`, para o fluxo
`gen_tests.py` → `jobe_test.py` → `gen_moodle_xml.py`. Use este caso quando o aluno
deve **implementar** uma função/programa, OU **completar/escrever um sketch Arduino**
(`setup()`/`loop()`), que é executado e corrigido por testes. (Para "mostrar código e
pedir análise/saída/enquete", use o brief **Cloze**; para consulta a banco, o **SQL**.)

## Layout `mdl/` (atual)
Os arquivos da questão ficam em **`<base>/mdl/`** (a raiz pode ter um projeto PlatformIO
para prototipar no Wokwi). Os scripts aceitam `<pasta>` ou `<pasta>/mdl`. `<base>` é o
**nome da pasta da questão**.

## Arquivos a gerar em `<base>/mdl/`
1. `question.json` — metadados (schema abaixo).
2. `questiontext.html` — enunciado em HTML (`<p>`, `<code>`, `<i>`, `<ul>`…).
3. `<base>_sol.cpp` — solução de referência CORRETA (define a função / o sketch pedido).
4. `answerpreload.cpp` — base do aluno (mesma assinatura + `// TODO`), sem resolver.
5. `<base>_cases.txt` — um caso por linha (as ENTRADAS; SEM `expected`). **Só para
   `*_function`/`*_program`** — o tipo `arduino` NÃO usa `cases.txt` (ver abaixo).

NÃO gerar `*_tests.json` (o `gen_tests.py` gera depois, rodando a referência).
(Nomes genéricos `sol.cpp`, `answerpreload.cpp`, `cases.txt` também são aceitos.)

## `question.json`
```json
{
  "name": "Titulo visivel no Moodle",
  "type": "c_function",
  "defaultgrade": 1,
  "allornothing": 1,
  "penaltyregime": "0, 10, 20, ...",
  "mocks": [],
  "defines": [],
  "call": "printf(\"%d\\n\", NOME_FUNC({}))"
}
```
- `type`:
  - `c_function` (C puro), `cpp_function` (C++ ou com mocks Arduino),
  - `c_program`/`cpp_program` (aluno escreve `main`; teste via `stdin`),
  - **`arduino`** (sketch `setup()`/`loop()` **sem `main`** — ver seção própria).
- `mocks`: `[]` para C/C++ puro; senão liste os headers mock necessários:
  `arduino-mock/Arduino.h` (bits, `String`, pinos), `arduino-mock/WiFi.h`,
  `arduino-mock/PubSubClient.h` (MQTT, c/ Last Will), `arduino-mock/esp32-hal-log.h`
  (log), `arduino-mock/DHT.h` (DHT22: 24.5/55.0), `arduino-mock/Ticker.h`.
  Com mocks, use `cpp_function` (ou `arduino`).
- `defines`: injeta `#define` antes dos mocks. Ex.: `["CORE_DEBUG_LEVEL=2"]` (filtra log).
- `call` (opcional, `*_function`): template de impressão com `{}` no lugar do argumento;
  permite o `cases.txt` ter só o argumento por linha. Especificador certo: `%d` int,
  `%ld` long, `%u` unsigned, `%.2f`/`%g` float/double, `%s` string (`.c_str()`), `%c` char.

## `<base>_cases.txt` (apenas `*_function`/`*_program`)
- Um caso por linha; `#` = comentário; linhas vazias ignoradas.
- Marcadores no fim: `@example` (exemplo visível "Por exemplo") e `@hide` (oculto).
- COM `call`: a linha é só o argumento (`-11 @example`; vários: `3, 7 @example`).
- SEM `call`: a linha é o testcode completo (`printf("%d\n", ehPar(4) ? 1 : 0) @example`).
  Não ponha `;` no fim (é acrescentado).
- Inclua ≥2 `@example` e ≥1 `@hide`; cubra bordas (0, negativos, limites).

## Tipo `arduino` — sketch `setup()`/`loop()` (sem `main`)
Para o aluno trabalhar na **base do Arduino**, inclusive "completar o código" (o
enunciado mostra trechos comentados que o aluno insere num esqueleto). O toolkit monta
o fonte como **mocks + código do aluno + um harness que chama `setup()` UMA vez**
(o `loop()` fica definido mas não roda).
- `question.json`: `{ "type": "arduino", "mocks": ["arduino-mock/Arduino.h", …] }`.
- **Não use `cases.txt`**: há **uma execução** e a **saída inteira** do sketch é o
  `expected` (o `gen_tests.py` gera o `tests.json` com esse único caso).
- `<base>_sol.cpp` = sketch completo e correto; `answerpreload.cpp` = o esqueleto com os
  locais a preencher (`// >>> insira A aqui`).
- No XML do Moodle vira `coderunnertype = cpp_program` com um template próprio que chama
  `setup()`. (Mesma saída no Jobe e no Moodle, pois usa os mesmos mocks.)

## Regras de qualidade (Jobe compila com -Wall -Werror)
- A referência precisa compilar SEM warnings. Loops de uma linha com chaves;
  evite variáveis não usadas.
- `answerpreload.cpp` tem a MESMA assinatura/estrutura da referência e NÃO resolve.
- C puro: `testcode` usa `printf` (o template já inclui `<stdio.h>`).
- Tamanho de tipos: host do Jobe é 64 bits; se depender do ESP32 (int 32 bits),
  use `int32_t`/`uint8_t` explícitos.

## Exemplo mínimo — `c_function` (ver `exemplos/coderunner-funcao/`)
`question.json`: `{"name":"C function: sqr","type":"c_function","call":"printf(\"%d\\n\", sqr({}))"}`
`sol.cpp`:
```c
int sqr(int n) { return n * n; }
```
`cases.txt`:
```text
-11   @example
9     @example
0
8     @hide
```

## Exemplo mínimo — `arduino` (ver `exemplos/coderunner-arduino/`)
`question.json`: `{"name":"Completar sketch: imprime 3 ciclos","type":"arduino","mocks":["arduino-mock/Arduino.h"]}`
`<base>_sol.cpp`:
```cpp
#include <Arduino.h>
void setup() {
  Serial.begin(115200);
  for (int i = 1; i <= 3; i++) { Serial.print("ciclo "); Serial.println(i); }
}
void loop() {}
```
`answerpreload.cpp`: o mesmo, com `// >>> insira A aqui` no lugar do `for`.
Saída esperada (gerada pelo `gen_tests.py`): `ciclo 1 / ciclo 2 / ciclo 3`.

## Exemplo com log (esp32-hal-log.h)
`{"type":"cpp_function" ou "arduino","mocks":["arduino-mock/esp32-hal-log.h", "arduino-mock/Arduino.h"]}`
Macros: `log_v/log_d/log_i/log_w/log_e` → saída `[V]/[D]/[I]/[W]/[E] msg`.
`"defines":["CORE_DEBUG_LEVEL=2"]` → só `log_w`/`log_e` aparecem (ensina filtragem).

## Comandos do autor (dentro do container de ferramentas)
```bash
gen_tests.py      quiz01/<base>     # entradas -> <base>_tests.json (roda a referência)
jobe_test.py      quiz01/<base>     # confere a referência (ou --answer entrega.cpp)
gen_moodle_xml.py quiz01            # valida (padrão) + grava quiz01/quiz_to_import.xml
```
(No host, sem o container: `python gen_tests.py …` com um Jobe em `http://localhost:4000`.)

## Pedido (preencher)
- **Base (nome da pasta):** …
- **Tipo (`c_function`/`cpp_function`/`*_program`/`arduino`):** …
- **Assinatura da função OU estrutura do sketch:** …
- **Enunciado (resumo):** …
- **Mocks necessários?** (Arduino / WiFi / PubSubClient / esp32-hal-log / DHT / Ticker / nenhum) …
- **defines?** (ex.: CORE_DEBUG_LEVEL) …
- **Casos de teste** (`*_function`/`*_program`; marque `@example` e `@hide`) OU, para
  `arduino`, **o sketch de referência + os trechos a completar**: …
- **Observações** (faixas, bordas, precisão, limites): …

> Saída esperada da IA: apenas os arquivos da pasta `<base>/mdl/`, cada um em bloco de
> código rotulado com o caminho. Sem `tests.json`.
