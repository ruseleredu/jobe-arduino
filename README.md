# jobe-arduino

Testar **lógica pura** de C/C++ e código estilo Arduino no sandbox **Jobe**
(Docker), sem hardware e sem Moodle — e **gerar questões CodeRunner** (XML) para
importar no Moodle a partir das mesmas pastas.

> Fronteira: isto testa lógica (bits, operadores, controle, tipos, funções,
> montagem de payload, callbacks MQTT). **Firmware real** (WiFi, GPIO, timing,
> broker) → `pio run` + **Wokwi**/ESP32 físico.

## Pré-requisitos
- **Docker** (único requisito para rodar — não precisa de g++ na máquina).
- **Python 3** (só biblioteca padrão; nada a instalar).

## Suba o Jobe
```bash
docker compose up -d          # usa o docker-compose.yml deste repo (Jobe em :4000)
curl http://localhost:4000/jobe/index.php/restapi/languages   # deve listar "c", "cpp", ...
```
Sem compose: `docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest`
(depois `docker start jobe` / `docker stop jobe`).

---

## Convenção de pasta por questão

Cada questão é uma pasta (o nome da pasta é a "base"). Ex.: `questions/sqr/`:

```
sqr/
├── question.json        # metadados (nome, tipo, nota, penaltyregime, mocks[])
├── questiontext.html    # enunciado (HTML)       → <questiontext> no Moodle
├── answerpreload.cpp    # base para o aluno      → <answerpreload>
├── sqr_sol.cpp          # solução de referência  → <answer>   (fallback: sol.cpp)
└── sqr_tests.json       # casos de teste         → <testcases> (fallback: tests.json)
```

**`question.json`:**
```json
{
  "name": "C function: sqr",
  "type": "c_function",
  "defaultgrade": 1,
  "allornothing": 1,
  "penaltyregime": "0, 10, 20, ...",
  "mocks": []
}
```
- `type`: `c_function`, `c_program`, `cpp_function`, `cpp_program`.
- `mocks`: vazio para C/C++ puro; `["arduino-mock/Arduino.h", ...]` para questões Arduino.

**`*_tests.json`** (alinhado ao CodeRunner — mesmo arquivo serve ao teste e ao XML):
```json
[
  { "testcode": "printf(\"%d\\n\", sqr(9))", "expected": "81", "example": true },
  { "testcode": "printf(\"%d\\n\", sqr(0))", "expected": "0", "display": "HIDE" }
]
```
- `testcode`: trecho que chama a função do aluno e imprime (sem `;` final — é acrescentado).
- `expected`: saída esperada. `stdin` (opcional): entrada no stdin.
- `example: true` → aparece na tabela "Por exemplo". `display: "HIDE"` → teste oculto.

> **Não escreva o `expected` à mão** — use o `gen_tests.py` (abaixo): você fornece só
> as entradas e ele calcula o `expected` rodando a solução de referência no Jobe.

### Gerar o tests.json a partir das entradas — `gen_tests.py`

Em vez de digitar os `expected`, descreva só os casos num arquivo simples e deixe a
referência calcular as saídas:

**`<base>_cases.txt`** (um caso por linha; `#` = comentário; marcadores `@example`/`@hide`):
```text
# com "call": "printf(\"%d\\n\", sqr({}))" no question.json -> a linha e so o argumento
-11    @example
9      @example
-1000
0
8      @hide
```
Sem o `call` no `question.json`, cada linha é o **testcode completo**
(ex.: `printf("%d\n", ehPar(4) ? 1 : 0)   @example`). Para casos com `stdin` ou mais
controle, use `cases.json` (lista de `{testcode|args, stdin?, example?, display?}`, sem `expected`).

```bash
python gen_tests.py questions/sqr               # grava questions/sqr/sqr_tests.json
python gen_tests.py questions --all             # todas as subpastas
python gen_tests.py questions/sqr --force       # sobrescreve tests.json existente
```

`question.json` pode trazer `"call"` (template com `{}`) para o caso homogêneo em que
só o argumento varia — aí o `cases.txt` fica com uma linha por argumento.

---

## Testar no Jobe — `jobe_test.py`

**Modo pasta** (recomendado): valida a solução de referência contra os testes
(como o "validate on save" do CodeRunner). `--jobe` tem default `http://localhost:4000`.

```bash
python jobe_test.py sqr                      # testa a referência (sqr_sol.cpp)
python jobe_test.py sqr --answer entrega.cpp # testa a entrega de um aluno
python jobe_test.py ehpar                     # questão com mock Arduino
```

**Modo flags** (legado — exemplos Arduino com harness e stdin):
```bash
python jobe_test.py \
  --mock arduino-mock/Arduino.h \
  --student exemplos/hello_sol.cpp \
  --harness harness/driver_sketch.cpp \
  --tests exemplos/hello_tests.json
```

Desfechos por caso: **OK** · **SAIDA DIFERENTE** (mostra esperado × obtido) ·
**ERRO DE COMPILACAO** (mostra o `cmpinfo`). Código de saída `0` só se todos passam.

---

## Gerar XML para o Moodle — `gen_moodle_xml.py`

```bash
python gen_moodle_xml.py questions/sqr                        # 1 questão → stdout
python gen_moodle_xml.py questions/sqr questions/ehpar -o banco.xml
python gen_moodle_xml.py questions -o banco.xml               # todas as subpastas de questions/
python gen_moodle_xml.py questions/* -o banco.xml             # idem (glob do shell)
```

Um argumento que é uma **pasta-questão** vira uma questão; um argumento que é uma
**pasta-contêiner** (ex.: `questions`) expande para todas as subpastas-questão. Assim
`questions` (contêiner) e `questions/*` (glob do bash) dão o mesmo resultado.

**Validação opcional antes de gerar** (`--validate`): roda a solução de referência
de cada questão no Jobe; se algum teste não passar, imprime o relatório e **não gera
o XML** (exit ≠ 0). Ideal para CI.

```bash
python gen_moodle_xml.py questions --validate -o banco.xml
# Jobe em outro host/porta: --jobe http://IP:4000  (--apikey se exigido)
```

Importe no Moodle em **Banco de questões → Importar → formato Moodle XML**.

**Questões com mocks Arduino:** quando `question.json` tem `mocks`, o gerador
embute o conteúdo dos mocks em `<globalextra>` e usa um `<template>` C++
determinístico (`globalextra` + resposta do aluno + `main` com o `testcode`), com
`type` `cpp_function`. Assim o aluno escreve só a função (ex.: `ehPar`) e o mock
de `Arduino.h` fica disponível na compilação dentro do CodeRunner.

---

## Fluxo recomendado
1. Crie a pasta: `questiontext.html`, `<base>_sol.cpp`, `answerpreload.cpp`,
   `question.json` e um `<base>_cases.txt` (só as entradas).
2. `python gen_tests.py <pasta>` → gera o `<base>_tests.json` (expected via referência).
3. `python jobe_test.py <pasta>` → confirme que a referência passa (ou teste uma entrega com `--answer`).
4. `python gen_moodle_xml.py <pasta> --validate -o banco.xml` → gera e importe no Moodle.

## Importante (Jobe é estrito)
O Jobe compila com `-Wall -Werror` (warnings viram erros). Mocks e código de apoio
precisam compilar limpos sob essas flags. Tipos: o host do Jobe é 64 bits — se o
teste depende do tamanho do ESP32, use `int32_t`/`uint8_t` explícitos.

## Estrutura do repo
```
jobe-arduino/
├── docker-compose.yml          # sobe o Jobe em :4000
├── jobe_test.py                # testa no Jobe (modo pasta + modo flags)
├── gen_tests.py                # gera tests.json das entradas (expected via referência)
├── gen_moodle_xml.py           # gera XML CodeRunner das pastas de questão
├── questions/                  # uma pasta por questão (sqr, ehpar, ...)
├── arduino-mock/               # Arduino.h, WiFi.h, PubSubClient.h (mocks)
├── harness/                    # drivers do modo flags
└── exemplos/                   # exemplos do modo flags (hello, payload, callback)
```
