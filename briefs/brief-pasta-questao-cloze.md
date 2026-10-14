# Brief — Pasta de questão Cloze (aluno ANALISA código)

Cole este brief num prompt de IA e preencha o "Pedido". A IA deve devolver os
arquivos de UMA pasta de questão do tipo **Cloze / Embedded Answers**
(`multianswer`) no padrão do toolkit `jobe-arduino`. Use este caso quando o código
é **apresentado** e o aluno compila/analisa e responde — colando a saída ou numa
enquete. (Para "o aluno escreve a função", use o brief **CodeRunner**.)

Por quê Cloze, e não CodeRunner: o CodeRunner é para o aluno *escrever* código
executado; para análise/leitura, o Cloze mistura texto + código exibido + campos
embutidos (resposta curta, numérica, múltipla escolha) na mesma questão.

## Arquivos a gerar em `<base>/`
1. `question.json` — `{ "name": "...", "type": "cloze", ... }` (schema abaixo).
2. `questiontext.html` — enunciado + `{{CODE}}` + campos Cloze (+ opcional `{{OUTPUT}}`).
3. `<base>_code.cpp` — o código EXIBIDO (programa completo, com `main`, saída determinística).

NÃO gerar `tests.json` nem `answerpreload.cpp` (não se aplicam ao Cloze).

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
- `code_type`: como o código é executado para `{{OUTPUT}}` (default `cpp_program`;
  use `c_program` se for C puro). Deve ser um PROGRAMA (tem `main`).
- `code_lang`: lexer do Pygments p/ `{{CODE}}` (default pela extensão: `.c`→c, `.cpp`→cpp).
- `stdin`, `mocks`, `defines`: como no CodeRunner (ex.: `defines` p/ `CORE_DEBUG_LEVEL`).

## Placeholders no `questiontext.html`
- `{{CODE}}` → o código exibido, com **syntax highlighting (Pygments)** e estilos
  inline (renderiza no Moodle sem CSS externo). Requer `pip install pygments`.
- `{{OUTPUT}}` → a **saída** do código, computada rodando-o no Jobe; pensada para ir
  DENTRO de um campo Cloze: `{1:SHORTANSWER:={{OUTPUT}}}` (preenche o esperado sozinho).
  Requer Jobe no ar. Ideal para saída de UMA linha/simples.
- `{{OUTPUT_BLOCK}}` → a mesma saída como bloco `<pre>` (para explicação/feedback).

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

## Exemplo mínimo (analisa_bits)
`question.json`: `{"name":"Analise: mascara AND","type":"cloze"}`
`analisa_bits_code.cpp`:
```c
#include <stdio.h>
#include <stdint.h>
int main(void) {
    uint8_t reg = 0b10110010, mask = 0b00001111;
    printf("%d\n", reg & mask);
    return 0;
}
```
`questiontext.html`:
```html
<p><strong>Compile e analise</strong> o programa abaixo.</p>
{{CODE}}
<p>1) Qual a saida? {1:SHORTANSWER:={{OUTPUT}}#Correto! reg &amp; mask isola os 4 bits baixos.}</p>
<p>2) O operador &amp; com 0b00001111 serve para:
{1:MULTICHOICE:=isolar os 4 bits baixos#Correto!~ligar os 4 bits altos#Seria OR~inverter os bits#Seria XOR}</p>
```

## Comandos do autor (depois de receber os arquivos)
```bash
pip install pygments
docker start jobe || docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest   # so se usar {{OUTPUT}}
python gen_moodle_xml.py questions/<base> -o banco.xml     # mistura com coderunner no mesmo banco
```
`{{CODE}}` não precisa de Jobe; `{{OUTPUT}}`/`{{OUTPUT_BLOCK}}` precisam. O
`--validate` pula questões Cloze (não há execução a validar).

## Pedido (preencher)
- **Base (nome da pasta):** …
- **Código a exibir** (ou peça para a IA escrever; precisa ter saída determinística): …
- **Como o aluno responde?** (colar a saída via SHORTANSWER / enquete MULTICHOICE / V-F / numérica): …
- **Mocks/defines no código?** (ex.: esp32-hal-log + CORE_DEBUG_LEVEL) …
- **Enunciado e alternativas da enquete (com feedback):** …

> Saída esperada da IA: apenas os arquivos da pasta `<base>/` (`question.json`,
> `questiontext.html`, `<base>_code.cpp`), cada um em bloco de código rotulado com o
> caminho. Sem `tests.json` nem `answerpreload.cpp`.
