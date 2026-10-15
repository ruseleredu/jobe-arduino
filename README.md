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

## Dois modos de uso

1. **Repo do toolkit (este):** tem os scripts, mocks e o `Dockerfile.pio-wokwi`.
   Construa a imagem autocontida uma vez (e, opcionalmente, publique no Docker Hub —
   veja `DOCKERHUB.md`):
   ```bash
   docker build -f Dockerfile.pio-wokwi -t ruseler/esp32-pio-wokwi:latest .
   ```
   O `docker compose up -d --build` aqui também constrói e sobe tudo. O build faz um
   **`pio run` de aquecimento** (projeto de teste ESP32/Arduino) para já instalar a
   plataforma e os toolchains na imagem — o 1º `pio run` em runtime fica rápido e
   offline. (O volume `pio-cache` é semeado com esse cache na 1ª execução.)

2. **Repo só de questões (recomendado para turmas):** contém **apenas** as questões
   e um `docker-compose.yml` que usa a imagem **pronta** `esp32-pio-wokwi:local` (sem
   `build`). Veja o modelo em `questions-repo-template/`. Dentro do container, o
   toolkit está no `PATH` e os mocks vêm de `JOBE_ARDUINO_HOME` (baked na imagem), então
   o repo de questões não carrega nenhum código do toolkit:
   ```bash
   docker compose up -d
   docker compose exec esp32-pio-wokwi bash
   new_question.py quiz01/minha_questao
   gen_tests.py quiz01/minha_questao && jobe_test.py quiz01/minha_questao
   gen_moodle_xml.py quiz01 --validate -o banco.xml
   ```

## Suba a stack (Jobe + container de ferramentas)
O `docker-compose.yml` sobe **dois** serviços na mesma rede:
- **`jobe`** — sandbox de correção (porta `4000` no host).
- **`esp32-pio-wokwi`** (`esp32-pio-wokwi:local`) — container com **PlatformIO Core**,
  **Wokwi CLI** e o toolkit (Python + Pygments), para validar o Jobe, testar as
  questões e ajudar a elaborá-las. O repo é montado em `/work`.

```bash
docker compose up -d --build          # sobe jobe + esp32-pio-wokwi (build na 1a vez)
curl http://localhost:4000/jobe/index.php/restapi/languages   # Jobe no ar? lista "c","cpp",...

# trabalhe dentro do container de ferramentas:
docker compose exec esp32-pio-wokwi bash
#   dentro dele JOBE_URL=http://jobe ja e o default de --jobe (porta 80 na rede do compose):
#   python gen_tests.py      questions/sqr
#   python jobe_test.py      questions/sqr
#   python gen_moodle_xml.py questions --validate -o banco.xml
#   pio run            # compilar firmware ESP32 (num projeto PlatformIO)
#   wokwi-cli .        # simular no Wokwi (precisa de WOKWI_CLI_TOKEN p/ CI)
```

Fora do container (no host), os scripts usam `http://localhost:4000` por padrão.
Só o Jobe, sem compose: `docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest`.

> O Wokwi CLI usa `WOKWI_CLI_TOKEN` (crie em wokwi.com/dashboard/ci). Exporte no host
> antes do `up` para repassá-lo ao container: `export WOKWI_CLI_TOKEN=...`.

---

## Criar uma questão nova — `new_question.py`

Inicializa a pasta da questão, cria um **projeto PlatformIO** (ESP32 + Arduino, VS
Code, sample-code) na raiz da pasta para prototipar/simular, e grava os
arquivos-base da questão em **`<base>/mdl/`** (Moodle), deixando a raiz do projeto
PIO limpa.

```bash
python new_question.py sqr                         # coderunner (default)
python new_question.py analise --type cloze        # cloze (análise de código)
python new_question.py blink --mocks arduino-mock/Arduino.h   # coderunner c/ mock (vira cpp_function)
python new_question.py x --no-pio                  # sem inicializar PlatformIO
python new_question.py quiz01/minha_questao        # caminho = contêiner/questao
python new_question.py blink-new --template blink  # copia templates/blink/ como base
```

O `pio project init` equivale a:
```bash
pio project init -b esp32dev -O "framework=arduino" -O "monitor_speed=115200" --ide vscode --sample-code
```
(roda dentro do container `esp32-pio-wokwi`, que tem o `pio`). Sem PlatformIO no
PATH, o script avisa e apenas cria os arquivos da questão. Depois edite os
arquivos-base e siga o fluxo do tipo (abaixo).

**`--template NOME`** copia uma pasta pronta de `templates/<NOME>/` (procurada no
diretório atual e depois no `JOBE_ARDUINO_HOME`) para a nova questão — projeto PIO
e `mdl/` juntos — e renomeia os arquivos `<NOME>_sol.cpp`, `<NOME>_cases.txt` etc.
para o novo nome. Nesse modo o `pio init` e os arquivos-base são pulados (o template
já é a base). Útil para partir de um esqueleto Wokwi/PIO padrão.

## Convenção de pasta por questão

Cada questão é uma pasta (o nome da pasta é a "base"). A raiz guarda o projeto
PlatformIO (para prototipar/simular) e os arquivos da questão ficam em **`mdl/`**.
Ex.: `questions/sqr/`:

```
sqr/
├── platformio.ini       # projeto PIO (prototipagem/simulação; opcional)
├── src/ include/ ...     # fontes do projeto PIO
└── mdl/                  # arquivos da questão (Moodle)
    ├── question.json        # metadados (nome, tipo, nota, penaltyregime, mocks[])
    ├── questiontext.html    # enunciado (HTML)       → <questiontext> no Moodle
    ├── answerpreload.cpp    # base para o aluno      → <answerpreload>
    ├── sqr_sol.cpp          # solução de referência  → <answer>   (fallback: sol.cpp)
    └── sqr_tests.json       # casos de teste         → <testcases> (fallback: tests.json)
```

> Todos os scripts (`gen_tests.py`, `jobe_test.py`, `gen_moodle_xml.py`) procuram os
> arquivos da questão em `<pasta>/mdl/` e, se `mdl/` não existir, na própria pasta
> (compatível com questões antigas sem `mdl/`). Com `--no-pio` a estrutura é a mesma:
> só a raiz fica sem o projeto PlatformIO.

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
python gen_tests.py questions/sqr               # grava questions/sqr/mdl/sqr_tests.json
python gen_tests.py questions --all             # todas as subpastas
python gen_tests.py questions/sqr --force       # sobrescreve tests.json existente
```

`question.json` pode trazer `"call"` (template com `{}`) para o caso homogêneo em que
só o argumento varia — aí o `cases.txt` fica com uma linha por argumento.

### Questões com log do ESP32 (`esp32-hal-log.h`)

Mock em `arduino-mock/esp32-hal-log.h`: macros `log_e/log_w/log_i/log_d/log_v` com
saída **determinística** `[<nível>] <msg>` (sem timestamp), respeitando
`CORE_DEBUG_LEVEL` (filtragem em tempo de compilação, como no ESP32). Níveis:
`NONE 0 · ERROR 1 · WARN 2 · INFO 3 · DEBUG 4 · VERBOSE 5` (default: VERBOSE).

- Declare o mock: `"mocks": ["arduino-mock/esp32-hal-log.h"]`, `"type": "cpp_function"`.
- Para fixar o nível (ensinar filtragem), use `"defines": ["CORE_DEBUG_LEVEL=2"]` no
  `question.json` — o define é injetado antes dos mocks (no build e no `globalextra`
  do XML). Exemplos prontos: `questions/logdemo` (nível 5, 5 linhas) e
  `questions/logfilter` (nível 2, só W e E).

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

## Questões de análise (Cloze / Embedded Answers)

Para "mostre o código, o aluno compila/analisa e responde" (colar a saída ou uma
enquete), o CodeRunner não é o ideal (ele é para o aluno *escrever* código). Use o
tipo **Cloze** (`multianswer`): texto + código exibido + campos embutidos.

Pasta (ex.: `questions/analisa_bits/`) — arquivos da questão em `mdl/`:
```
analisa_bits/
└── mdl/
    ├── question.json            # { "name": "...", "type": "cloze" }
    ├── questiontext.html        # enunciado + {{CODE}} + campos Cloze (sintaxe abaixo)
    └── analisa_bits_code.cpp     # código EXIBIDO (entra onde está {{CODE}})
```
Placeholders no `questiontext.html` (substituídos na geração):
- `{{CODE}}` → o código exibido (de `<base>_code.cpp`/`<base>_sol.cpp`), com
  **syntax highlighting via Pygments** e estilos **inline** (renderiza no Moodle sem
  CSS externo). Sem Pygments instalado, cai para `<pre><code>` simples.
- `{{OUTPUT}}` → a **saída** do código, computada rodando-o no Jobe. Pensado para ir
  **dentro de um campo** Cloze (ex.: `{1:SHORTANSWER:={{OUTPUT}}}`) — o `expected` é
  preenchido sozinho, como no `gen_tests`. Requer Jobe no ar.
- `{{OUTPUT_BLOCK}}` → a mesma saída como bloco `<pre>` (para explicação/feedback).

`question.json` (cloze) aceita: `code_type` (como rodar o código p/ `{{OUTPUT}}`;
default `cpp_program`), `code_lang` (lexer do Pygments; default pela extensão),
`stdin`, `mocks`, `defines`. Dependência: `pip install pygments`. Cloze não usa
`tests.json`/`gen_tests`; o `--validate` pula cloze (não há execução a validar), mas
`{{OUTPUT}}` sempre exige Jobe.

```bash
python gen_moodle_xml.py questions/analisa_bits -o banco.xml   # mistura com coderunner no mesmo banco
```

### Sintaxe Cloze (campos embutidos)
Forma geral: `{PESO:TIPO:opções}`. Dentro das opções: `=` marca a resposta certa,
`~` separa alternativas, `%NN%` dá crédito parcial, `#` adiciona feedback.

- **Resposta curta** (colar a saída/valor): `{1:SHORTANSWER:=2}`
  (sem distinção de maiúsculas; use `SHORTANSWER_C` para diferenciar).
- **Numérica** (aceita tolerância): `{1:NUMERICAL:=2:0}` (`=valor:erro`).
- **Enquete/múltipla escolha**:
  - menu suspenso: `{1:MULTICHOICE:=Certa~Errada1~Errada2}`
  - rádio vertical: `{1:MULTICHOICE_V:=...}` · horizontal: `{1:MULTICHOICE_H:=...}`
- **Múltipla resposta** (caixas): `{2:MULTIRESPONSE:=A~=B~C}` (várias corretas com `=`).
- **Feedback por alternativa**: `{1:MULTICHOICE:=Certa#Boa!~Errada#Reveja X}`.
- **Crédito parcial**: `{1:SHORTANSWER:=exato~%50%aproximado}`.

Exemplo real em `questions/analisa_bits/questiontext.html` (saída via `SHORTANSWER`
+ duas enquetes `MULTICHOICE`). O `{{CODE}}` embute o programa exibido.

## Fluxo recomendado
1. Crie a pasta (ex.: `new_question.py <pasta>`): em `mdl/` ficam `questiontext.html`,
   `<base>_sol.cpp`, `answerpreload.cpp`, `question.json` e um `<base>_cases.txt` (só as entradas).
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
├── new_question.py             # inicializa pasta de questão (PIO na raiz + arquivos em mdl/)
├── jobe_test.py                # testa no Jobe (modo pasta + modo flags)
├── gen_tests.py                # gera tests.json das entradas (expected via referência)
├── gen_moodle_xml.py           # gera XML CodeRunner das pastas de questão
├── questions/                  # uma pasta por questão (sqr, ehpar, ...); arquivos em <q>/mdl/
├── templates/                  # esqueletos p/ new_question.py --template (opcional)
├── arduino-mock/               # Arduino.h, WiFi.h, PubSubClient.h, esp32-hal-log.h (mocks)
├── harness/                    # drivers do modo flags
└── exemplos/                   # exemplos do modo flags (hello, payload, callback)
```
