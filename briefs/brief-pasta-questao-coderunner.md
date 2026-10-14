# Brief — Pasta de questão CodeRunner (aluno ESCREVE código)

Cole este brief num prompt de IA e preencha o "Pedido". A IA deve devolver os
arquivos de UMA pasta de questão no padrão do toolkit `jobe-arduino`, para o fluxo
`gen_tests.py` → `jobe_test.py` → `gen_moodle_xml.py`. Use este caso quando o aluno
deve **implementar** uma função/programa que é executado e corrigido por testes.
(Para "mostrar código e pedir análise/saída/enquete", use o brief **Cloze**.)

## Arquivos a gerar em `<base>/`
1. `question.json` — metadados (schema abaixo).
2. `questiontext.html` — enunciado em HTML (`<p>`, `<code>`, `<i>`, `<ul>`…).
3. `<base>_sol.cpp` — solução de referência CORRETA (define a função pedida).
4. `answerpreload.cpp` — base do aluno (mesma assinatura + `// TODO`), sem resolver.
5. `<base>_cases.txt` — um caso por linha (as ENTRADAS; SEM `expected`).

NÃO gerar `*_tests.json` (o `gen_tests.py` gera depois, rodando a referência).

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
- `type`: `c_function` (C puro), `cpp_function` (C++ ou com mocks Arduino),
  `c_program`/`cpp_program` (aluno escreve `main`; teste via `stdin`).
- `mocks`: `[]` para C/C++ puro; senão liste os headers mock necessários:
  `arduino-mock/Arduino.h` (bits, `String`, pinos), `arduino-mock/WiFi.h`,
  `arduino-mock/PubSubClient.h` (MQTT), `arduino-mock/esp32-hal-log.h` (log).
  Com mocks, use `type: cpp_function`.
- `defines`: injeta `#define` antes dos mocks. Ex.: `["CORE_DEBUG_LEVEL=2"]` para
  fixar o nível de log (filtra `log_i/d/v`).
- `call` (opcional): template de impressão com `{}` no lugar do argumento; permite o
  `cases.txt` ter só o argumento por linha. Especificador certo: `%d` int, `%ld`
  long, `%u` unsigned, `%.2f`/`%g` float/double, `%s` string, `%c` char.

## `<base>_cases.txt`
- Um caso por linha; `#` = comentário; linhas vazias ignoradas.
- Marcadores no fim: `@example` (exemplo visível "Por exemplo") e `@hide` (oculto).
- COM `call`: a linha é só o argumento (`-11 @example`; vários: `3, 7 @example`).
- SEM `call`: a linha é o testcode completo (`printf("%d\n", ehPar(4) ? 1 : 0) @example`).
  Não ponha `;` no fim (é acrescentado).
- Inclua ≥2 `@example` e ≥1 `@hide`; cubra bordas (0, negativos, limites).

## Regras de qualidade (Jobe compila com -Wall -Werror)
- A referência precisa compilar SEM warnings. Loops de uma linha com chaves;
  evite variáveis não usadas.
- `answerpreload.cpp` tem a MESMA assinatura da referência e NÃO resolve.
- C puro: `testcode` usa `printf` (o template já inclui `<stdio.h>`).
- Tamanho de tipos: host do Jobe é 64 bits; se depender do ESP32 (int 32 bits),
  use `int32_t`/`uint8_t` explícitos.

## Exemplo mínimo (sqr)
`question.json`: `{"name":"C function: sqr","type":"c_function","call":"printf(\"%d\\n\", sqr({}))"}`
`questiontext.html`: `<p>Escreva <code>int sqr(int n)</code> que retorne o quadrado de <i>n</i>.</p>`
`sqr_sol.cpp`:
```c
int sqr(int n) { return n * n; }
```
`answerpreload.cpp`:
```c
int sqr(int n) {
    // TODO: retorne o quadrado de n
    return 0;
}
```
`sqr_cases.txt`:
```text
-11   @example
9     @example
-1000
0
8     @hide
```

## Exemplo com log (esp32-hal-log.h)
`question.json`: `{"name":"...","type":"cpp_function","mocks":["arduino-mock/esp32-hal-log.h"],"call":"mostrarLogs({})"}`
Macros no `sol.cpp`: `log_v/log_d/log_i/log_w/log_e` (saída `[V]/[D]/[I]/[W]/[E] msg`).
Para ensinar filtragem, acrescente `"defines":["CORE_DEBUG_LEVEL=2"]` (só W e E saem).

## Comandos do autor (depois de receber os arquivos)
```bash
docker start jobe || docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest
python gen_tests.py      questions/<base>                 # entradas -> <base>_tests.json
python jobe_test.py      questions/<base>                 # confere a referencia
python gen_moodle_xml.py questions --validate -o banco.xml # valida e gera o banco
```

## Pedido (preencher)
- **Base (nome da pasta):** …
- **Assinatura / tipo (`c_function`/`cpp_function`/`*_program`):** …
- **Enunciado (resumo):** …
- **Mocks necessários?** (Arduino / WiFi / PubSubClient / esp32-hal-log / nenhum) …
- **defines?** (ex.: CORE_DEBUG_LEVEL) …
- **Casos de teste** (entradas; marque `@example` e `@hide`): …
- **Observações** (faixas, bordas, precisão, limites): …

> Saída esperada da IA: apenas os 5 arquivos da pasta `<base>/`, cada um em bloco de
> código rotulado com o caminho. Sem `tests.json`.
