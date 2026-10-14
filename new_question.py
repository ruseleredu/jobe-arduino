#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
new_question.py — inicializa a pasta de uma questao do toolkit jobe-arduino.

- Cria questions/<base>/
- Inicializa um projeto PlatformIO (ESP32 + Arduino, VS Code, sample-code) para
  o autor prototipar/compilar/simular (pio run / wokwi-cli).
- Grava os arquivos-base conforme o tipo:
    coderunner (default): question.json, questiontext.html, <base>_sol.cpp,
                          answerpreload.cpp, <base>_cases.txt
    cloze:                question.json, questiontext.html, <base>_code.cpp

Uso:
  python new_question.py sqr                      # coderunner (default)
  python new_question.py analise --type cloze
  python new_question.py blink --type coderunner --mocks arduino-mock/Arduino.h
  python new_question.py x --dir questions --name "Titulo" --no-pio --force

PlatformIO init equivalente a:
  pio project init -b esp32dev -O "framework=arduino" -O "monitor_speed=115200" \
      --ide vscode --sample-code
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


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
    path.write_text(conteudo, encoding="utf-8")
    print(f"  criado: {path}", file=sys.stderr)


def base_coderunner(folder, base, nome, mocks):
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
    w(folder / "question.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    w(folder / "questiontext.html",
      f"<p>TODO: enunciado de <code>{base}</code>.</p>\n")
    inc = '#include <Arduino.h>\n\n' if cpp else ""
    w(folder / f"{base}_sol.cpp",
      f"{inc}// Solucao de REFERENCIA (correta). Define a funcao pedida.\n"
      f"int {base}(int n) {{\n    return n;  // TODO\n}}\n")
    w(folder / "answerpreload.cpp",
      f"{inc}// Base entregue ao aluno (mesma assinatura, sem resolver).\n"
      f"int {base}(int n) {{\n    // TODO\n    return 0;\n}}\n")
    w(folder / f"{base}_cases.txt",
      "# Entradas de teste. Com \"call\" no question.json, a linha e so o argumento.\n"
      "# Marcadores no fim: @example (exemplo visivel) e @hide (teste oculto).\n"
      "1    @example\n"
      "2    @example\n"
      "3    @hide\n")


def base_cloze(folder, base, nome):
    meta = {
        "name": nome,
        "type": "cloze",
        "penalty": 0.3333333,
        "code_type": "cpp_program",
        "code_lang": "cpp",
    }
    w(folder / "question.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    w(folder / f"{base}_code.cpp",
      "#include <stdio.h>\n\n"
      "int main(void) {\n"
      "    // TODO: codigo a ser EXIBIDO (saida deterministica)\n"
      "    printf(\"%d\\n\", 40 + 2);\n"
      "    return 0;\n"
      "}\n")
    w(folder / "questiontext.html",
      "<p><strong>Compile e analise</strong> o programa abaixo.</p>\n\n"
      "{{CODE}}\n\n"
      "<p>1) Qual e a saida impressa?<br>\n"
      "{1:SHORTANSWER:={{OUTPUT}}#TODO feedback}</p>\n\n"
      "<p>2) (Enquete) TODO pergunta conceitual:<br>\n"
      "{1:MULTICHOICE:=Alternativa certa#Correto!~Alternativa errada#Reveja.}</p>\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Inicializa a pasta de uma questao (PIO + arquivos-base).")
    ap.add_argument("base", help="pasta/questao: nome simples (ex.: sqr) ou caminho (ex.: quiz01/minha_questao)")
    ap.add_argument("--type", choices=["coderunner", "cloze"], default="coderunner",
                    help="tipo da questao (default: coderunner)")
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

    if not args.no_pio:
        run_pio_init(folder)

    cont = folder.parent  # contêiner (ex.: quiz01 ou questions) p/ gerar o banco
    if args.type == "cloze":
        base_cloze(folder, base, nome)
        prox = (f"python gen_moodle_xml.py {folder} -o banco.xml   "
                "# {{OUTPUT}} precisa do Jobe no ar")
    else:
        base_coderunner(folder, base, nome, args.mocks)
        prox = (f"python gen_tests.py {folder}\n"
                f"  python jobe_test.py {folder}\n"
                f"  python gen_moodle_xml.py {cont} --validate -o banco.xml")

    print(f"\nPasta criada: {folder}  (tipo: {args.type})", file=sys.stderr)
    print("Edite os arquivos-base e depois:", file=sys.stderr)
    print("  " + prox, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
