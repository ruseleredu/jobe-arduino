#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
new_question.py — inicializa a pasta de uma questao do toolkit jobe-arduino.

- Cria questions/<base>/
- Inicializa um projeto PlatformIO (ESP32 + Arduino, VS Code, sample-code) para
  o autor prototipar/compilar/simular (pio run / wokwi-cli). A raiz da pasta fica
  com o projeto PIO; os arquivos da questao (Moodle) ficam em <base>/mdl/.
- Grava os arquivos-base (em <base>/mdl/) conforme o tipo:
    coderunner (default): question.json, questiontext.html, <base>_sol.cpp,
                          answerpreload.cpp, <base>_cases.txt
    cloze:                question.json, questiontext.html, <base>_code.cpp

Alternativa: --template NOME copia uma pasta pronta de templates/<NOME>/ como base
(projeto + mdl/), renomeando os arquivos <NOME>_* para <base>_*. Pula o pio init.

Uso:
  python new_question.py sqr                      # coderunner (default)
  python new_question.py analise --type cloze
  python new_question.py blink --type coderunner --mocks arduino-mock/Arduino.h
  python new_question.py x --dir questions --name "Titulo" --no-pio --force
  python new_question.py blink-new --template blink      # copia templates/blink/

PlatformIO init equivalente a:
  pio project init -b esp32dev -O "framework=arduino" -O "monitor_speed=115200" \
      --ide vscode --sample-code
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

TOOLKIT_HOME = os.environ.get("JOBE_ARDUINO_HOME") or os.path.dirname(os.path.abspath(__file__))

# prefixos de arquivos da questao que carregam o <base> no nome (renomeados no --template)
SUFIXOS_BASE = ["_sol.cpp", "_sol.c", "_code.cpp", "_code.c", "_code.ino", "_code.py",
                "_cases.txt", "_cases.json", "_tests.json"]


def run_pio_init(folder):
    """Roda `pio project init` na pasta. Retorna True se ok, False se pio ausente/erro."""
    if shutil.which("pio") is None and shutil.which("platformio") is None:
        print("aviso: PlatformIO (pio) nao encontrado no PATH — pulando o projeto PIO.", file=sys.stderr)
        return False
    exe = "pio" if shutil.which("pio") else "platformio"
    cmd = [exe, "project", "init", "-d", str(folder),
           "-b", "esp32dev",
           "-O", "framework=arduino",
           "-O", "monitor_speed=115200",
           "--ide", "vscode", "--sample-code"]
    print("+ " + " ".join(cmd), file=sys.stderr)
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print("aviso: `pio project init` falhou — a pasta da questao foi criada mesmo assim.", file=sys.stderr)
        return False
    return True


def w(path, conteudo):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(conteudo, encoding="utf-8")
    print(f"  criado: {path}", file=sys.stderr)


def base_coderunner(mdl, base, nome, mocks):
    cpp = bool(mocks)
    qtype = "cpp_function" if cpp else "c_function"
    meta = {
        "name": nome,
        "type": qtype,
        "defaultgrade": 1,
        "allornothing": 1,
        "penaltyregime": "0, 10, 20, ...",
        "mocks": mocks,
        "call": f'printf("%d\\n", {base}({{}}))',
    }
    w(mdl / "question.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    w(mdl / "questiontext.html",
      f"<p>TODO: enunciado de <code>{base}</code>.</p>\n")
    inc = '#include <Arduino.h>\n\n' if cpp else ""
    w(mdl / f"{base}_sol.cpp",
      f"{inc}// Solucao de REFERENCIA (correta). Define a funcao pedida.\n"
      f"int {base}(int n) {{\n    return n;  // TODO\n}}\n")
    w(mdl / "answerpreload.cpp",
      f"{inc}// Base entregue ao aluno (mesma assinatura, sem resolver).\n"
      f"int {base}(int n) {{\n    // TODO\n    return 0;\n}}\n")
    w(mdl / f"{base}_cases.txt",
      "# Entradas de teste. Com \"call\" no question.json, a linha e so o argumento.\n"
      "# Marcadores no fim: @example (exemplo visivel) e @hide (teste oculto).\n"
      "1    @example\n"
      "2    @example\n"
      "3    @hide\n")


def base_cloze(mdl, base, nome):
    meta = {
        "name": nome,
        "type": "cloze",
        "penalty": 0.3333333,
        "code_type": "cpp_program",
        "code_lang": "cpp",
    }
    w(mdl / "question.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    w(mdl / f"{base}_code.cpp",
      "#include <stdio.h>\n\n"
      "int main(void) {\n"
      "    // TODO: codigo a ser EXIBIDO (saida deterministica)\n"
      "    printf(\"%d\\n\", 40 + 2);\n"
      "    return 0;\n"
      "}\n")
    w(mdl / "questiontext.html",
      "<p><strong>Compile e analise</strong> o programa abaixo.</p>\n\n"
      "{{CODE}}\n\n"
      "<p>1) Qual e a saida impressa?<br>\n"
      "{1:SHORTANSWER:={{OUTPUT}}#TODO feedback}</p>\n\n"
      "<p>2) (Enquete) TODO pergunta conceitual:<br>\n"
      "{1:MULTICHOICE:=Alternativa certa#Correto!~Alternativa errada#Reveja.}</p>\n")


def achar_template(nome):
    """Resolve templates/<nome>/ no CWD e depois no TOOLKIT_HOME."""
    for raiz in (Path("templates"), Path(TOOLKIT_HOME) / "templates"):
        cand = raiz / nome
        if cand.is_dir():
            return cand
    return None


def renomear_prefixo(d, antigo, novo):
    """Renomeia <antigo>_sol.cpp -> <novo>_sol.cpp etc. dentro de d (se existir)."""
    if antigo == novo or not d.is_dir():
        return
    for suf in SUFIXOS_BASE:
        src = d / f"{antigo}{suf}"
        if src.is_file():
            dst = d / f"{novo}{suf}"
            src.rename(dst)
            print(f"  renomeado: {src.name} -> {dst.name}", file=sys.stderr)


def copiar_template(nome, folder):
    """Copia templates/<nome>/ para folder, renomeando arquivos <nome>_* -> <base>_*.
    Atualiza question.json['name'] se for igual ao nome antigo. Retorna True/False."""
    src = achar_template(nome)
    if src is None:
        print(f"ERRO: template nao encontrado: templates/{nome} "
              f"(procurei no CWD e em {TOOLKIT_HOME}/templates)", file=sys.stderr)
        return False
    base = folder.name
    print(f"+ copiando template '{nome}' ({src}) -> {folder}", file=sys.stderr)
    shutil.copytree(src, folder, dirs_exist_ok=True)
    # renomeia os arquivos prefixados pelo nome antigo, na raiz e em mdl/
    for d in (folder, folder / "mdl"):
        renomear_prefixo(d, nome, base)
    # ajusta o 'name' no question.json se ele era o nome antigo
    for mj in (folder / "mdl" / "question.json", folder / "question.json"):
        if mj.is_file():
            try:
                meta = json.loads(mj.read_text(encoding="utf-8"))
                if meta.get("name") in (nome, None):
                    meta["name"] = base
                    mj.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass
            break
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description="Inicializa a pasta de uma questao (PIO + arquivos-base em mdl/).")
    ap.add_argument("base", help="pasta/questao: nome simples (ex.: sqr) ou caminho (ex.: quiz01/minha_questao)")
    ap.add_argument("--type", choices=["coderunner", "cloze"], default="coderunner",
                    help="tipo da questao (default: coderunner)")
    ap.add_argument("--template", help="copia templates/<NOME>/ como base (pula pio init e arquivos-base)")
    ap.add_argument("--dir", default="questions",
                    help="pasta-contêiner usada SO quando 'base' e um nome simples (default: questions)")
    ap.add_argument("--name", help="titulo visivel no Moodle (default: o <base>)")
    ap.add_argument("--mocks", nargs="*", default=[],
                    help="coderunner: mocks a declarar (ex.: arduino-mock/Arduino.h)")
    ap.add_argument("--no-pio", action="store_true", help="nao inicializar projeto PlatformIO")
    ap.add_argument("--force", action="store_true", help="usar a pasta mesmo se ja existir")
    args = ap.parse_args(argv)

    # 'base' com separador ("quiz01/minha_questao") e um caminho relativo ao CWD;
    # nome simples ("sqr") vai sob --dir. O prefixo dos arquivos e o ultimo componente.
    arg = args.base.replace("\\", "/").strip("/")
    folder = Path(arg) if "/" in arg else Path(args.dir) / arg
    base = folder.name
    if folder.exists() and not args.force:
        ap.error(f"{folder} ja existe (use --force)")
    folder.mkdir(parents=True, exist_ok=True)
    nome = args.name or base
    cont = folder.parent  # contêiner (ex.: quiz01 ou questions) p/ gerar o banco

    # ---- modo template: copia uma pasta pronta e para por aqui ----
    if args.template:
        if not copiar_template(args.template, folder):
            return 2
        if args.name:  # usuario forcou um titulo
            for mj in (folder / "mdl" / "question.json", folder / "question.json"):
                if mj.is_file():
                    meta = json.loads(mj.read_text(encoding="utf-8"))
                    meta["name"] = nome
                    mj.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    break
        print(f"\nPasta criada a partir do template '{args.template}': {folder}", file=sys.stderr)
        print("Edite os arquivos (raiz = projeto PIO; mdl/ = questao) e depois:", file=sys.stderr)
        print(f"  python gen_tests.py {folder}\n"
              f"  python jobe_test.py {folder}\n"
              f"  python gen_moodle_xml.py {cont} --validate -o banco.xml", file=sys.stderr)
        return 0

    # ---- modo padrao: pio init na raiz + arquivos-base em mdl/ ----
    if not args.no_pio:
        run_pio_init(folder)

    mdl = folder / "mdl"
    mdl.mkdir(parents=True, exist_ok=True)

    if args.type == "cloze":
        base_cloze(mdl, base, nome)
        prox = (f"python gen_moodle_xml.py {folder} -o banco.xml   "
                "# {{OUTPUT}} precisa do Jobe no ar")
    else:
        base_coderunner(mdl, base, nome, args.mocks)
        prox = (f"python gen_tests.py {folder}\n"
                f"  python jobe_test.py {folder}\n"
                f"  python gen_moodle_xml.py {cont} --validate -o banco.xml")

    print(f"\nPasta criada: {folder}  (tipo: {args.type}; arquivos da questao em {mdl})", file=sys.stderr)
    print("Edite os arquivos-base e depois:", file=sys.stderr)
    print("  " + prox, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
