# Exemplos — um de cada tipo de questão

Cada pasta é uma questão completa no layout `mdl/`, já **validada** (com o
`*_tests.json` gerado quando se aplica). Use como ponto de partida ou com
`new_question.py <nova> --template <esta pasta>`.

| Pasta                 | `type`        | O que é                                               |
| --------------------- | ------------- | ----------------------------------------------------- |
| `coderunner-funcao/`  | `c_function`  | aluno escreve `int sqr(int n)` (corrigida por casos)  |
| `coderunner-arduino/` | `arduino`     | aluno completa um **sketch** `setup()/loop()` (3 ciclos) |
| `cloze/`              | `cloze`       | aluno **analisa** um sketch (máscara XOR) e responde  |
| `sql/`                | `sql`         | aluno escreve um `SELECT ... GROUP BY` (média por grupo) |

## Gerar o banco XML de um exemplo
Dentro do container de ferramentas (`esp32-pio-wokwi`) ou com o toolkit no PATH:

```bash
gen_tests.py      exemplos/coderunner-funcao     # (re)gera o tests.json quando aplicável
gen_moodle_xml.py exemplos/coderunner-funcao     # grava exemplos/coderunner-funcao/mdl/quiz_to_import.xml
# ou todos juntos num banco só:
gen_moodle_xml.py exemplos/* -o exemplos/banco-exemplos.xml
```

O arquivo `banco-exemplos.xml` (incluído) já traz os quatro tipos num único banco,
pronto para importar no Moodle (Banco de questões → Importar → Moodle XML).

Saídas esperadas (geradas pela referência): `coderunner-arduino` → `ciclo 1/2/3`;
`sql` → `a|27.9` e `b|22.0`.
