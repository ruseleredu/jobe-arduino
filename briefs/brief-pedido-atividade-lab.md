# Brief — Pedido de nova atividade de laboratório

Cole este brief junto com o pedido e preencha só o que muda (tema e tarefas). Ele
define o padrão fixo do curso; o assistente entrega a aula pronta e validada.

## Contexto e stack
- **Plataforma:** ESP32 · **Ambiente:** PlatformIO (VS Code) · **Framework:** Arduino.
- **Simulador:** **Wokwi** (sem placa física). **Broker/telemetria:** stack Docker (Mosquitto + Node-RED + MQTT Explorer).
- **Documentação:** Docusaurus em **MDX**. **Entrega/correção:** Git + GitHub Actions, por commit.
- **Organização:** `ELT85B-N21-2026-2`. Repos por aula: `labNN-template`, `labNN-grupo-a/b/c…`, e `labNN-grupo-n` = **repositório de notas/correção** daquela aula (mesmo padrão para `projeto-*`).

## Formato do documento (MDX Docusaurus)
- Front matter completo (`id`, `title`, `sidebar_label`, `sidebar_position`, `slug`, `keywords`).
- Avisos como **admonitions** (`:::info/tip/warning/danger/note`); `<Tabs>`/`<TabItem>` quando útil; diagramas em ```mermaid``` (requer `@docusaurus/theme-mermaid`).
- `import CommitPoint from '@site/src/components/CommitPoint';` no topo.
- Code blocks com `title="..."`. Seções típicas: Objetivos, Material, Setup, Partes (experimentos com saída esperada), Projeto integrador, Desafios D1–D4, Gabarito (em `<details>` atrás de `:::danger Spoiler`), Checklist.
- **Regra MDX (crítica):** todo código com `<`, `>`, `{`, `}`, `&` fica em blocos/backticks; **nunca** use esses caracteres nas strings `task="..."` dos CommitPoint.
- Nota `:::info` explicando quando o código fica em `setup()` (demonstração única) vs `loop()` (comportamento contínuo).

## Wokwi
- Incluir `diagram.json` (circuito) e `wokwi.toml` (`.pio/build/<env>/firmware.bin` e `.elf`). Fluxo: Build → "Wokwi: Start Simulator". Recompilar antes de simular.
- WiFi no Wokwi: SSID `Wokwi-GUEST`, senha vazia; broker **público** (`broker.hivemq.com:1883`). Broker **local** no Wokwi exige o **IoT Gateway** (Wokwi Club). ESP32 físico → broker local direto (IP da máquina, não `localhost`).
- (Opcional) Verificação de saída serial no CI: cenário `test/*.test.yaml` (`wait-serial`) + `WOKWI_CLI_TOKEN`.

## Pontos de commit (componente CommitPoint)
- Marcar cada tarefa avaliada: `<CommitPoint task="descrição" pontos={N} />`. Numeração **automática** T1…Tn na ordem do documento.
- Props: `type`, `files` (multi: `files="a.cpp b.ini"`), `prefix`, `push`, `n`, `id` (âncora), `allowEmpty` (deploy/release, sem mudar arquivos), `run` (comando extra, ex.: alias de deploy).
- Convenção: **1 tarefa = 1 commit** cuja mensagem começa com `Tn:`. Vale o commit `Tn:` mais recente; refazer > desfazer; nunca `push --force` no repo de grupo.
- Passos de runtime (subir stack, testar MQTT, deploy) → salvar **evidência** em `evidencias/*.txt` (checável) ou `allowEmpty`.

## Pontuação (padrão)
- Somar **100 pts** (o autograder normaliza p/ 0–10). Ex.: experimentos ~5 cada, projeto 15–25, desafios 10 cada. Ajustar conforme o nº de tarefas.

## Correção automática
- **`grade.py`** (no `labNN-grupo-n`): `TAREFAS` = `token`, `nome`, `pontos`, `checks`. Tipos de check: `contem`, `nao_contem`, `compila` (`pio run`), `release` (gh api), `jobe` (executa no sandbox). Correção **por commit** (`git worktree`); gera `GRADE.md` + `nota.csv`.
- Repo `labNN-grupo-n` autoconfigurável: deduz a aula pelo nome, descobre os grupos, corrige em paralelo (reutilizável `grade-one.yml` + `grade-all.yml`), lê grupos **read-only** (org secret `STUDENTS_TOKEN`), grava boletins em `notas/`. À prova de adulteração.
- **`gen_grade.py`**: gera o scaffold do `grade.py` a partir dos CommitPoint do MDX (`-o grade.py`) e tem modo **`--check`** (compara MDX × `grade.py`, aponta divergências — para CI).
- **Lógica pura no Jobe (sem Moodle):** mocks `Arduino.h`/`WiFi.h`/`PubSubClient.h` + harness + `jobe_test.py` (`--local`/`--jobe`) para avaliar comportamento (ver brief do Jobe). Firmware real → `pio run` + Wokwi.

## Fluxo ao criar a aula
1. Escrever a aula em MDX com `CommitPoint` em cada tarefa (validar: `gen_grade.py aula.mdx --tarefas-only` deve listar T1…Tn com os pontos certos).
2. Varrer MDX: nenhum `<`/`{` solto fora de código (só JSX de `CommitPoint`/`Tabs`/`details`).
3. `gen_grade.py aula.mdx -o autograde/grade.py` → completar os `checks`.
4. (Opcional) cenário Wokwi / check `jobe` no CI.

## Modelo de pedido (preencher)
- **Tema / número (`labNN`):** …
- **Objetivos de aprendizagem:** …
- **Periféricos/circuito no Wokwi:** (LEDs, botões, sensores, I²C/SPI, MQTT…) …
- **Tarefas avaliadas** (viram `CommitPoint` T1…Tn) e **pontos** de cada: …
- **Checagens por tarefa** (`contem`/`compila`/`jobe`/saída serial/`release`): …
- **Desafios/gabarito?** (sim/não) · **Usa Docker/Node-RED?** (sim/não)

## Regras de qualidade do entregável
- Precisão técnica **para ESP32** (ex.: `int`/`word` = 4 bytes, `double` = 8 bytes; difere do Uno) — verificar quando o tamanho importa.
- Buscar detalhes de ferramentas que mudam (versões de extensões/plugins, Wokwi, CodeRunner/Jobe) antes de afirmar.
- Código com saída esperada ("preveja antes de rodar"); gabarito testável.
- Validar o que der: extração dos CommitPoint, compilação de exemplos, parsing de configs.
