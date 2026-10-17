# Brief — Pasta de questão Cloze (aluno ANALISA código)

Cole este brief num prompt de IA e preencha o "Pedido". A IA deve devolver os
arquivos de UMA pasta de questão do tipo **Cloze / Embedded Answers**
(`multianswer`) no padrão do toolkit `jobe-arduino`. Use este caso quando o código
é **apresentado** e o aluno compila/analisa e responde — colando a saída ou numa
enquete. (Para "o aluno escreve a função/sketch", use o brief **CodeRunner**.)

Por quê Cloze, e não CodeRunner: o CodeRunner é para o aluno *escrever* código
executado; para análise/leitura, o Cloze mistura texto + código exibido + campos
embutidos (resposta curta, numérica, múltipla escolha) na mesma questão.

## Layout `mdl/` (atual)
Os arquivos ficam em **`<base>/mdl/`**. `<base>` é o nome da pasta.

## Arquivos a gerar em `<base>/mdl/`
1. `question.json` — `{ "name": "...", "type": "cloze", ... }` (schema abaixo).
2. `questiontext.html` — enunciado + `{{CODE}}` + campos Cloze (+ opcional `{{OUTPUT}}`).
3. `<base>_code.cpp` — o código EXIBIDO (saída determinística).

NÃO gerar `tests.json` nem `answerpreload.cpp` (não se aplicam ao Cloze).
(`code.cpp` genérico também é aceito.)

## `question.json`
```json
{
  "name": "Titulo visivel no Moodle",
  "type": "cloze",
  "penalty": 0.3333333,
  "code_type": "cpp_program",
  "code_lang": "cpp",
  "stdin": "",
  "mocks": [],
  "defines": []
}
```
- `code_type`: como o código é executado para `{{OUTPUT}}`:
  - `cpp_program` (default) / `c_program` → o código é um PROGRAMA (tem `main`).
  - **`arduino`** → o código é um **sketch** `setup()/loop()` (sem `main`); o harness
    chama `setup()` uma vez. Útil para colar no PlatformIO/Wokwi. Requer os mocks
    (ex.: `"mocks": ["arduino-mock/Arduino.h"]`).
- `code_lang`: lexer do Pygments p/ `{{CODE}}` (default pela extensão; use `sql`, `c`, `cpp`…).
- `stdin`, `mocks`, `defines`: como no CodeRunner (ex.: `defines` p/ `CORE_DEBUG_LEVEL`).

## Placeholders no `questiontext.html`
- `{{CODE}}` → o código exibido, com **syntax highlighting (Pygments)** e estilos
  inline (renderiza no Moodle sem CSS externo). Requer `pip install pygments`.
- `{{OUTPUT}}` → a **saída** do código, computada rodando-o no Jobe; pensada para ir
  DENTRO de um campo Cloze: `{1:SHORTANSWER:={{OUTPUT}}}` (preenche o esperado sozinho).
  Requer Jobe no ar. Ideal para saída de UMA linha/simples.
- `{{OUTPUT_BLOCK}}` → a mesma saída como bloco `<pre>` (para explicação/feedback).

Quando NÃO usar `{{OUTPUT}}`: se a saída real varia ou tem timestamp/IP (WiFi, MQTT,
log do ESP32 com prefixo real), prefira um Cloze **conceitual** (pergunte o conceito,
com resposta fixa) em vez de "qual é a saída exata".

## Sintaxe Cloze (campos embutidos)
Forma geral `{PESO:TIPO:opções}` — `=` resposta certa, `~` separa, `%NN%` crédito
parcial, `#` feedback.
- **Resposta curta (colar valor):** `{1:SHORTANSWER:=42}` (use `SHORTANSWER_C` p/ diferenciar maiúsculas).
- **Numérica (com tolerância):** `{1:NUMERICAL:=42:0}` (`=valor:erro`).
- **Enquete/múltipla escolha:** menu `{1:MULTICHOICE:=Certa~Errada1~Errada2}`,
  rádio `MULTICHOICE_V`/`MULTICHOICE_H`.
- **Múltipla resposta (caixas):** `{2:MULTIRESPONSE:=A~=B~C}`.
- **Feedback por alternativa:** `{1:MULTICHOICE:=Certa#Boa!~Errada#Reveja X}`.

Dica: saída MULTI-LINHA não cabe bem em `SHORTANSWER` (uma linha). Para isso, prefira
uma enquete "Qual a saída correta?" com o bloco certo (use `{{OUTPUT_BLOCK}}` ou
cole a saída) entre distratores.

## Exemplo mínimo (ver `exemplos/cloze/` — sketch Arduino, máscara XOR)
`question.json`:
```json
{"name":"Analise: mascara XOR","type":"cloze","code_type":"arduino","code_lang":"cpp","mocks":["arduino-mock/Arduino.h"]}
```
`code.cpp` (sketch):
```cpp
#include <Arduino.h>
void printBin(uint8_t v) { for (int i = 7; i >= 0; i--) Serial.print(bitRead(v, i)); Serial.println(); }
void setup() {
  Serial.begin(115200);
  uint8_t reg = 0b10110010, mask = 0b00001111;
  printBin(reg ^ mask);
}
void loop() {}
```
`questiontext.html`:
```html
<p><strong>Compile e analise</strong> o sketch (roda uma vez no setup()).</p>
{{CODE}}
<p>1) Qual a saida (8 bits)? {1:SHORTANSWER:={{OUTPUT}}#Correto! XOR inverte os bits onde a mascara vale 1.}</p>
<p>2) XOR com 0b00001111: {1:MULTICHOICE:=inverte os 4 bits baixos#Correto!~zera os 4 baixos#Seria AND~liga os 4 baixos#Seria OR}</p>
```
(Para C puro clássico: `code_type` `c_program`/`cpp_program` e um `int main()` no code.)

## Comandos do autor (depois de receber os arquivos)
```bash
pip install pygments
gen_moodle_xml.py quiz01/<base>     # {{OUTPUT}} precisa do Jobe no ar; grava <base>/mdl/quiz_to_import.xml
```
`{{CODE}}` não precisa de Jobe; `{{OUTPUT}}`/`{{OUTPUT_BLOCK}}` precisam. O
`--validate` (ligado por padrão) pula Cloze (não há execução a validar).

## Pedido (preencher)
- **Base (nome da pasta):** …
- **Código a exibir** (programa ou sketch Arduino; precisa ter saída determinística): …
- **`code_type`** (`cpp_program` / `c_program` / `arduino`): …
- **Como o aluno responde?** (SHORTANSWER / enquete MULTICHOICE / V-F / numérica): …
- **Mocks/defines no código?** (ex.: Arduino.h; esp32-hal-log + CORE_DEBUG_LEVEL) …
- **Enunciado e alternativas da enquete (com feedback):** …

> Saída esperada da IA: apenas os arquivos da pasta `<base>/mdl/` (`question.json`,
> `questiontext.html`, `<base>_code.cpp`), cada um em bloco de código rotulado com o
> caminho. Sem `tests.json` nem `answerpreload.cpp`.
