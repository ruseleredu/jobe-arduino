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
docker compose exec esp32-pio-wokwi bash
# dentro do container (o toolkit esta no PATH; mocks e templates vem de JOBE_ARDUINO_HOME):
new_question.py quiz01/minha_questao          # cria pasta: PIO na raiz + arquivos em mdl/
new_question.py quiz01/analise --type cloze
new_question.py quiz01/pisca --template blink # parte de um template baked na imagem
gen_tests.py      quiz01/minha_questao
jobe_test.py      quiz01/minha_questao
gen_moodle_xml.py quiz01          # valida (padrão) + grava quiz01/quiz_to_import.xml
```

## Estrutura sugerida
```
meu-quiz-repo/
├── docker-compose.yml     # este (usa a imagem pronta)
├── quiz01/                # um "contêiner" por lista/prova
│   ├── minha_questao/
│   │   ├── platformio.ini # projeto PIO (prototipar/simular) — raiz limpa
│   │   └── mdl/           # arquivos da questao (question.json, _sol.cpp, _cases.txt, ...)
│   └── analise/
│       └── mdl/
└── banco.xml              # gerado (importar no Moodle)
```
Os arquivos da questão ficam em `<questao>/mdl/`; os scripts procuram lá (e caem
para a raiz se não houver `mdl/`). `JOBE_URL=http://jobe`, `JOBE_ARDUINO_HOME`
(mocks e `templates/`) já vêm da imagem/compose — não precisa passar `--jobe` nem
carregar os mocks aqui.
