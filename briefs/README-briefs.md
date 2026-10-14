# README dos briefs — qual usar em cada situação

Índice dos briefs reutilizáveis do curso (ESP32 / PlatformIO / Wokwi / Docker / Jobe
/ Moodle). Cada brief é markdown puro, feito para **colar num prompt de IA** e
preencher o bloco "Pedido". Comece por este índice e vá ao brief certo.

## Mapa rápido

| Quero… | Use o brief | Entrega |
|---|---|---|
| Pedir uma **aula de laboratório** (MDX Docusaurus, Wokwi, CommitPoints) | `brief-pedido-atividade-lab.md` | uma aula `.mdx` + arquivos de apoio |
| Entender/usar o **teste de Arduino no Jobe** (sem Moodle) | `brief-jobe-arduino.md` | referência técnica (mocks, harness, `jobe_test.py`) |
| Criar questão em que o aluno **ESCREVE código** (corrigida por testes) | `brief-pasta-questao-coderunner.md` | pasta de questão CodeRunner |
| Criar questão em que o aluno **ANALISA código** (cola saída / enquete) | `brief-pasta-questao-cloze.md` | pasta de questão Cloze |

Para o **aluno**, há ainda `como-funciona-avaliacao.md` (como a entrega por commits
vira nota) — não é um brief de IA, é material de leitura.

## Como decidir o brief da questão
- O aluno deve **implementar** uma função/programa? → **CodeRunner**.
- O código é **dado** e o aluno **lê/analisa** (qual a saída? qual alternativa?)? → **Cloze**.
- Em dúvida: se a correção precisa **executar o código do aluno**, é CodeRunner; se
  precisa só **conferir uma resposta** (texto/opção), é Cloze.

## Contexto comum a todos
- **Organização:** `ELT85B-N21-2026-2`; repos por aula `labNN-grupo-*`, notas em `labNN-grupo-n`.
- **Correção de código:** sandbox **Jobe** (Docker, `-Wall -Werror`).
  `docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest`
- **Toolkit `jobe-arduino/`:** `jobe_test.py` (testa no Jobe), `gen_tests.py` (gera
  `tests.json` das entradas, expected via referência), `gen_moodle_xml.py` (gera XML
  CodeRunner/Cloze; `--validate` roda a referência antes de gerar).
- **Mocks:** `arduino-mock/` (`Arduino.h`, `WiFi.h`, `PubSubClient.h`, `esp32-hal-log.h`).
- **Dependências:** Docker + Python 3; `pip install pygments` (só p/ `{{CODE}}` do Cloze).

## Fluxos (resumo)
**Aula:** preencher `brief-pedido-atividade-lab.md` → recebe a aula MDX com CommitPoints.

**Questão CodeRunner:**
```bash
python gen_tests.py      questions/<base>
python jobe_test.py      questions/<base>
python gen_moodle_xml.py questions --validate -o banco.xml
```

**Questão Cloze:**
```bash
pip install pygments
python gen_moodle_xml.py questions/<base> -o banco.xml   # Jobe no ar se usar {{OUTPUT}}
```

Importação no Moodle (ambos os tipos): **Banco de questões → Importar → Moodle XML**.
