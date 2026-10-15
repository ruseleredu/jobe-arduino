# Repositório de questões (usa a imagem esp32-pio-wokwi:local)

Este repo contém **apenas questões**. O toolkit (scripts, mocks, harness) vive dentro
da imagem `esp32-pio-wokwi:local`, construída a partir do repositório dedicado do
toolkit (`Dockerfile.pio-wokwi`).

## Pré-requisitos
- A imagem `ruseler/esp32-pio-wokwi:latest` (Docker Hub). O compose a baixa sozinho;
  ou `docker compose pull`. (Para construir localmente, veja o repo do toolkit / `DOCKERHUB.md`.)
- (Opcional) Token do Wokwi no `.env`: `cp .env.example .env` e preencha `WOKWI_CLI_TOKEN`.

## Usar (neste repo de questões)
```bash
docker compose pull
docker compose up -d
# cada ferramenta como um comando único (sem entrar no shell):
docker compose exec esp32-pio-wokwi bash -c "new_question.py quiz01/minha_questao"   # PIO na raiz + arquivos em mdl/
docker compose exec esp32-pio-wokwi bash -c "new_question.py quiz01/analise --type cloze"
docker compose exec esp32-pio-wokwi bash -c "new_question.py quiz01/pisca --template blink"  # template baked na imagem
docker compose exec esp32-pio-wokwi bash -c "gen_tests.py quiz01/minha_questao"
docker compose exec esp32-pio-wokwi bash -c "jobe_test.py quiz01/minha_questao"
docker compose exec esp32-pio-wokwi bash -c "gen_moodle_xml.py quiz01"   # valida + grava quiz01/quiz_to_import.xml
```

### Atalhos no VS Code
Para não repetir o prefixo, defina funções no terminal integrado (rode da raiz do repo):
```bash
# ~/.bashrc / ~/.zshrc
ja() { docker compose exec esp32-pio-wokwi bash -c "$*"; }
nq() { ja "new_question.py $*"; }   # nq quiz01/minha_questao
gt() { ja "gen_tests.py $*"; }      # gt quiz01/minha_questao
jt() { ja "jobe_test.py $*"; }      # jt quiz01/minha_questao
gx() { ja "gen_moodle_xml.py $*"; } # gx quiz01
```
Ou use as **tarefas** já incluídas em `.vscode/tasks.json` (Command Palette → *Run
Task*): elas rodam na pasta do arquivo aberto (os scripts aceitam tanto a pasta da
questão quanto o `.../mdl`).

## Estrutura sugerida
```
meu-quiz-repo/
├── docker-compose.yml     # este (usa a imagem pronta)
├── .vscode/tasks.json     # tarefas "Run Task" (gen_tests, jobe_test, gen_moodle_xml, nova questao)
├── quiz01/                # um "contêiner" por lista/prova
│   ├── minha_questao/
│   │   ├── platformio.ini # projeto PIO (prototipar/simular) — raiz limpa
│   │   └── mdl/           # arquivos da questao (question.json, _sol.cpp, _cases.txt, ...)
│   └── analise/
│       └── mdl/
└── quiz01/quiz_to_import.xml   # gerado (importar no Moodle)
```
Os arquivos da questão ficam em `<questao>/mdl/`; os scripts procuram lá (e caem
para a raiz se não houver `mdl/`), e aceitam tanto `quiz01/minha_questao` quanto
`quiz01/minha_questao/mdl`. `JOBE_URL=http://jobe`, `JOBE_ARDUINO_HOME` (mocks e
`templates/`) já vêm da imagem/compose — não precisa passar `--jobe` nem carregar os
mocks aqui.
