# esp32-pio-wokwi — publicar no Docker Hub

Imagem de ferramentas para elaborar/validar questões de C/C++ e ESP32:
**PlatformIO Core** (`pio`), **Wokwi CLI** (`wokwi-cli`), **Python + Pygments** e o
toolkit `jobe-arduino` (scripts, mocks, harness) já embutidos em `/opt/jobe-arduino`
(no `PATH`; `JOBE_ARDUINO_HOME` aponta para lá). O toolchain ESP32/Arduino vem
pré-instalado (o build faz um `pio run` de aquecimento).

Imagem: **`ruseler/esp32-pio-wokwi`**

## Pré-requisitos
- Docker com login no Docker Hub: `docker login`
- Rede para baixar PlatformIO, Wokwi CLI e os toolchains (o build é grande na 1ª vez).

## Build e push
No repositório do toolkit (onde estão `Dockerfile.pio-wokwi` e os scripts/mocks):

```bash
# build (amd64) — a tag ja fica pronta para o push
docker build --platform linux/amd64 -f Dockerfile.pio-wokwi -t ruseler/esp32-pio-wokwi:latest .

# (opcional) uma tag de versao, alem de latest
docker tag ruseler/esp32-pio-wokwi:latest ruseler/esp32-pio-wokwi:1.0

# publica
docker push ruseler/esp32-pio-wokwi:latest
docker push ruseler/esp32-pio-wokwi:1.0
```

> **Arquitetura:** o Wokwi CLI embutido é o binário **linux x64** estático, então
> publique para `linux/amd64`. Em Apple Silicon, use `--platform linux/amd64` (roda via
> emulação). Uma variante arm64 exigiria trocar o binário do Wokwi CLI no Dockerfile.

### Teste rápido antes do push
```bash
docker run --rm ruseler/esp32-pio-wokwi:latest bash -lc \
  "pio --version && wokwi-cli --help >/dev/null && echo OK && ls \$JOBE_ARDUINO_HOME"
```

## Usar a imagem (quem só consome)
Num repositório só de questões, o `docker-compose.yml` referencia a imagem publicada
(sem `build`) e sobe o Jobe junto:

```bash
docker compose pull          # baixa ruseler/esp32-pio-wokwi:latest e o jobe
docker compose up -d
docker compose exec esp32-pio-wokwi bash
# dentro: new_question.py / gen_tests.py / jobe_test.py / gen_moodle_xml.py / pio / wokwi-cli
```

## `.env` para o WOKWI_CLI_TOKEN
O token do Wokwi (para `wokwi-cli` em modo CI) **não** vai na imagem — fica num
`.env` ao lado do `docker-compose.yml`. O Compose lê o `.env` automaticamente.

1. `cp .env.example .env`
2. edite: `WOKWI_CLI_TOKEN=wok_xxx...` (crie em https://wokwi.com/dashboard/ci)
3. `docker compose up -d`

No compose, o serviço recebe o token assim:
```yaml
    environment:
      - WOKWI_CLI_TOKEN=${WOKWI_CLI_TOKEN:-}
```
`.env` está no `.gitignore` — **não** versione o token. O `Jobe` e o `PlatformIO`
não precisam do token; ele só é usado ao simular no Wokwi CI.

## Atualizar a imagem
Ao mudar scripts/mocks/Dockerfile, refaça o build e o push (`:latest` e, se quiser,
uma nova tag de versão). Quem consome atualiza com `docker compose pull`.
