# README dos briefs — qual usar em cada situação

Índice dos briefs reutilizáveis do curso (ESP32 / PlatformIO / Wokwi / Docker / Jobe
/ Moodle). Cada brief é markdown puro, feito para **colar num prompt de IA** e
preencher o bloco "Pedido". Comece por este índice e vá ao brief certo.

## Mapa rápido

| Quero… | Use o brief | Entrega |
|---|---|---|
| Pedir uma **aula de laboratório** (MDX Docusaurus, Wokwi, CommitPoints) | `brief-pedido-atividade-lab.md` | uma aula `.mdx` + arquivos de apoio |
| Entender/usar o **teste de Arduino no Jobe** (sem Moodle) | `brief-jobe-arduino.md` | referência técnica (mocks, harness, `jobe_test.py`) |
| Criar questão em que o aluno **ESCREVE código** (função OU sketch "completar o código") | `brief-pasta-questao-coderunner.md` | pasta de questão CodeRunner |
| Criar questão em que o aluno **ANALISA código** (cola saída / enquete) | `brief-pasta-questao-cloze.md` | pasta de questão Cloze |
| Criar questão de **SQL** (aluno escreve a consulta, roda no sqlite3 do Jobe) | `brief-pasta-questao-sql.md` | pasta de questão SQL |

Para o **aluno**, há ainda `como-funciona-avaliacao.md` (como a entrega por commits
vira nota) — não é um brief de IA, é material de leitura.

Em `exemplos/` há **um exemplo pronto e validado de cada tipo** (ver abaixo).

## Como decidir o brief da questão
- O aluno deve **implementar** uma função ou **completar um sketch**? → **CodeRunner**
  (brief coderunner; o tipo `arduino` cobre o sketch `setup()/loop()`).
- O código é **dado** e o aluno **lê/analisa** (qual a saída? qual alternativa?)? → **Cloze**.
- É **consulta a banco de dados** (SELECT/JOIN/GROUP BY…)? → **SQL**.
- Em dúvida: se a correção precisa **executar o código do aluno**, é CodeRunner/SQL; se
  precisa só **conferir uma resposta** (texto/opção), é Cloze.

## Convenção de pasta (atual) — `mdl/`
Cada questão é uma pasta cujo **nome é a "base"**. Os arquivos da questão (Moodle)
ficam em **`<base>/mdl/`**; a raiz guarda, opcionalmente, o **projeto PlatformIO** para
prototipar no Wokwi. Os scripts procuram em `<base>/mdl/` (e caem para a raiz se não
houver `mdl/`), e aceitam tanto `<pasta>` quanto `<pasta>/mdl` como argumento.

```
minha_questao/
├── platformio.ini   # projeto PIO (opcional; prototipar/simular)
├── src/ …
└── mdl/             # arquivos da questão (o que vira XML do Moodle)
    ├── question.json
    ├── questiontext.html
    └── … (varia por tipo; ver cada brief)
```

## Criar a pasta — `new_question.py`
```bash
new_question.py quiz01/minha_questao                 # coderunner (default) + PIO + mdl/
new_question.py quiz01/analise --type cloze          # cloze
new_question.py quiz01/x --no-pio                    # sem projeto PlatformIO
new_question.py quiz01/y --template <nome>           # copia templates/<nome>/ como base
```

## Contexto comum a todos
- **Organização:** `ELT85B-N21-2026-2`; repos por aula `labNN-grupo-*`, notas em `labNN-grupo-n`.
- **Correção de código:** sandbox **Jobe** (Docker, `-Wall -Werror`; linguagens `c`,
  `cpp`, `sqlite3`, …). Na stack do curso o Jobe escuta a porta **80 na rede do compose**
  (host: `4000:80`); dentro do container de ferramentas o default é `JOBE_URL=http://jobe`.
- **Imagem de ferramentas `esp32-pio-wokwi`** (Docker): traz PlatformIO Core, Wokwi CLI,
  Python+Pygments e o toolkit `jobe-arduino` já embutido (scripts no PATH, mocks e
  `templates/` em `JOBE_ARDUINO_HOME`). Uso típico:
  ```bash
  docker compose up -d
  docker compose exec esp32-pio-wokwi bash -c "gen_tests.py quiz01/minha_questao"
  docker compose exec esp32-pio-wokwi bash -c "jobe_test.py quiz01/minha_questao"
  docker compose exec esp32-pio-wokwi bash -c "gen_moodle_xml.py quiz01"
  ```
- **Toolkit `jobe-arduino/`:** `new_question.py` (inicializa a pasta), `gen_tests.py`
  (gera `tests.json` das entradas, expected via referência), `jobe_test.py` (testa no
  Jobe), `gen_moodle_xml.py` (gera XML CodeRunner/Cloze/SQL).
- **`gen_moodle_xml.py` — padrões atuais:** **valida no Jobe por padrão** (use
  `--no-validate` para pular) e, sem `-o`, grava em **`<pasta>/mdl/quiz_to_import.xml`**
  (1 questão) ou no diretório-pai comum (várias). `-o arquivo.xml` escolhe; `-o -` → stdout.
- **Mocks (`arduino-mock/`):** `Arduino.h`, `WiFi.h`, `PubSubClient.h` (com Last Will),
  `esp32-hal-log.h`, `DHT.h`, `Ticker.h`.
- **Dependências:** Docker + Python 3; `pip install pygments` (só p/ `{{CODE}}` do Cloze).

## Tipos de questão (resumo)
| Tipo (`question.json`) | Aluno faz | Arquivos-chave em `mdl/` | Correção |
|---|---|---|---|
| `c_function`/`cpp_function` | escreve a **função** | `question.json`, `questiontext.html`, `<base>_sol.cpp`, `answerpreload.cpp`, `<base>_cases.txt` | Jobe executa cada caso |
| `arduino` (sketch) | **completa/escreve o sketch** `setup()`/`loop()` (sem `main`) | idem acima (sem `cases.txt`); 1 execução, saída inteira = esperado | Jobe chama `setup()` 1x |
| `cloze` | **analisa** o código exibido | `question.json`, `questiontext.html`, `<base>_code.cpp` (+`schema`… não) | compara resposta (texto/opção) |
| `sql` | escreve a **consulta** | `question.json`, `questiontext.html`, `schema.sql`, `<base>_sol.sql` | sqlite3 no Jobe |

## Fluxos (resumo)
**Aula:** preencher `brief-pedido-atividade-lab.md` → recebe a aula MDX com CommitPoints.

**CodeRunner (função ou arduino):**
```bash
gen_tests.py      quiz01/<base>     # entradas -> <base>_tests.json
jobe_test.py      quiz01/<base>     # confere a referência
gen_moodle_xml.py quiz01            # valida + grava quiz01/quiz_to_import.xml
```

**Cloze:**
```bash
pip install pygments
gen_moodle_xml.py quiz01/<base>     # Jobe no ar se usar {{OUTPUT}}
```

**SQL:**
```bash
gen_tests.py      quiz01/<base>     # roda a consulta de referência -> expected
gen_moodle_xml.py quiz01/<base>
```

Importação no Moodle (todos os tipos): **Banco de questões → Importar → Moodle XML**.

## Exemplos prontos (`exemplos/`)
Um de cada tipo, já no layout `mdl/` e **validados** (com `*_tests.json` gerado):
- `exemplos/coderunner-funcao/` — `c_function` (`sqr`).
- `exemplos/coderunner-arduino/` — `arduino` (completar o sketch; imprime 3 ciclos).
- `exemplos/cloze/` — `cloze` (sketch Arduino + `{{CODE}}`/`{{OUTPUT}}`, máscara XOR).
- `exemplos/sql/` — `sql` (média por grupo com `GROUP BY`).

Gere o banco de um exemplo com, p.ex.: `gen_moodle_xml.py exemplos/sql`.
