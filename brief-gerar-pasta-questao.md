# Brief — Gerar a pasta de uma questão (CodeRunner/Jobe)

Cole este brief num prompt de IA e preencha o "Pedido" no fim. A IA deve devolver
os arquivos de UMA pasta de questão no padrão do toolkit `jobe-arduino`, prontos
para `gen_tests.py` → `jobe_test.py` → `gen_moodle_xml.py`.

## Contexto do toolkit
- Correção de código em C/C++ no sandbox **Jobe** (Docker, `-Wall -Werror`), e
  geração de questões **CodeRunner** (XML) para o Moodle a partir de pastas.
- Cada questão = uma **pasta** (o nome da pasta é a "base", ex.: `sqr`).
- O `expected` dos testes NÃO é escrito à mão: o `gen_tests.py` roda a solução de
  referência no Jobe e preenche. O autor fornece só as **entradas**.

## Arquivos que a IA deve gerar na pasta `<base>/`
1. `question.json` — metadados (ver schema abaixo).
2. `questiontext.html` — enunciado em HTML (pode usar `<p>`, `<code>`, `<i>`…).
3. `<base>_sol.cpp` — solução de referência CORRETA (define a função pedida).
4. `answerpreload.cpp` — base que o aluno recebe (assinatura + `// TODO`), sem resolver.
5. `<base>_cases.txt` — um caso por linha (as ENTRADAS; sem `expected`).

NÃO gerar `*_tests.json` (é gerado depois pelo `gen_tests.py`).

## Schema do `question.json`
```json
{
  "name": "Titulo visivel no Moodle",
  "type": "c_function",
  "defaultgrade": 1,
  "allornothing": 1,
  "penaltyregime": "0, 10, 20, ...",
  "mocks": [],
  "call": "printf(\"%d\\n\", NOME_FUNC({}))"
}
```
- `type`: `c_function` (C puro), `cpp_function` (C++ ou com mocks Arduino),
  `c_program`/`cpp_program` (aluno escreve `main`, teste via stdin).
- `mocks`: `[]` para C/C++ puro; `["arduino-mock/Arduino.h"]` (e/ou `WiFi.h`,
  `PubSubClient.h`) quando a função usa recursos Arduino (bits, `String`, etc.).
  Com mocks, use `type: cpp_function`.
- `call` (opcional): template de impressão com `{}` no lugar do argumento; permite
  o `cases.txt` conter só o argumento por linha. Escolha o especificador certo:
  `%d` int, `%ld` long, `%u` unsigned, `%.2f`/`%g` float/double, `%s` string,
  `%c` char. Omita `call` quando os casos variam muito (aí cada linha é o testcode completo).

## Formato do `<base>_cases.txt`
- Um caso por linha; `#` inicia comentário; linhas vazias ignoradas.
- Marcadores no fim: `@example` (vira exemplo visível "Por exemplo") e `@hide`
  (teste oculto). Padrão: visível e não-exemplo.
- COM `call`: a linha é só o argumento (ex.: `-11 @example`). Vários argumentos:
  `3, 7 @example`.
- SEM `call`: a linha é o testcode completo (ex.:
  `printf("%d\n", ehPar(4) ? 1 : 0)   @example`). Não ponha `;` no fim (é acrescentado).
- Inclua ao menos 2 `@example` e 1 `@hide`. Cubra casos de borda (0, negativos,
  limites) e faça os exemplos serem representativos.

## Regras de qualidade (Jobe é estrito)
- A referência precisa compilar com `-Wall -Werror` (sem warnings). Para globais em
  header/mocks, prefira evitar "unused"; para loops de uma linha, use chaves.
- `answerpreload.cpp` deve ter a MESMA assinatura da referência e NÃO resolver.
- Em C puro o `testcode` usa `printf` (o template já inclui `<stdio.h>`); em C++
  pode usar `printf`/`cout`.
- Tamanho de tipos: host do Jobe é 64 bits; se o enunciado depende do ESP32 (int de
  32 bits), use `int32_t`/`uint8_t` explícitos no enunciado e na referência.

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

## Depois de receber os arquivos (comandos que o autor roda)
```bash
docker start jobe || docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest
python gen_tests.py      questions/<base>            # entradas -> <base>_tests.json
python jobe_test.py      questions/<base>            # confere a referencia
python gen_moodle_xml.py questions --validate -o banco.xml   # valida e gera o banco
```

## Pedido (preencher)
- **Base (nome da pasta):** …
- **Assinatura da função / tipo de questão:** … (ex.: `int sqr(int)`, c_function)
- **Enunciado (resumo):** …
- **Usa recursos Arduino?** (não / quais mocks) …
- **Casos de teste desejados** (entradas; marque exemplos e ocultos): …
- **Observações** (faixas, bordas, precisão, limites): …

> Saída esperada da IA: apenas os 5 arquivos da pasta `<base>/`, cada um em seu
> bloco de código rotulado com o caminho, prontos para salvar. Sem `tests.json`.
