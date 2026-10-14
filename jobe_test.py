#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jobe_test.py — testa codigo estilo Arduino/C (PlatformIO) no sandbox Jobe (Docker).

Dois modos:

1) MODO PASTA (recomendado) — tudo de uma questao numa pasta (nome = base):
     python jobe_test.py sqr
   Le de sqr/:
     question.json      -> tipo (c_function/c_program/cpp_*), mocks[]
     sqr_sol.cpp        -> solucao de referencia (ou sol.cpp)      [o "aluno" testado]
     sqr_tests.json     -> casos [{testcode, stdin, expected, ...}] (ou tests.json)
     answerpreload.cpp  -> base do aluno (usado so pelo XML do Moodle; aqui ignorado)
     questiontext.html  -> enunciado (idem)
   Para testar a entrega de um aluno em vez da referencia:
     python jobe_test.py sqr --answer entrega_do_aluno.cpp

2) MODO FLAGS (legado) — mock(s)/student/harness/tests avulsos (stdin+stdout):
     python jobe_test.py --mock arduino-mock/Arduino.h \\
       --student exemplos/hello_sol.cpp --harness harness/driver_sketch.cpp \\
       --tests exemplos/hello_tests.json

Pre-requisito: um Jobe rodando. Via Docker:
  docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest
"""
import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

OK = 15  # outcome de sucesso do Jobe
DEFAULT_JOBE = "http://localhost:4000"

FUNCTION_TYPES = {"c_function", "cpp_function"}
PROGRAM_TYPES = {"c_program", "cpp_program"}


def _strip_includes(text, nomes):
    """Remove os #include dos headers mockados (angle ou quote)."""
    if not nomes:
        return text
    alt = "|".join(re.escape(n) for n in nomes)
    pat = re.compile(r'^\s*#\s*include\s*[<"]\s*(' + alt + r')\s*[>"]\s*$', re.M)
    return pat.sub("// (include de mock removido)", text)


# ---------- modo FLAGS: mocks + aluno + harness ----------
def build_source(mock_paths, student_path, harness_path):
    nomes = [Path(m).name for m in mock_paths]
    partes = [_strip_includes(Path(m).read_text(encoding="utf-8"), nomes) for m in mock_paths]
    aluno = _strip_includes(Path(student_path).read_text(encoding="utf-8"), nomes)
    harness = Path(harness_path).read_text(encoding="utf-8")
    return ("\n".join(partes) + "\n// ===== codigo do aluno =====\n" + aluno
            + "\n// ===== harness =====\n" + harness + "\n")


# ---------- modo PASTA: mocks + aluno + (main gerado do testcode) ----------
def lang_de(qtype, mocks):
    if mocks:
        return "cpp"                         # mocks Arduino sao C++
    if qtype in ("c_function", "c_program"):
        return "c"
    if qtype in ("cpp_function", "cpp_program"):
        return "cpp"
    if qtype == "python3":
        return "python3"
    return "cpp"


def preamble_de(lang, mocks):
    if mocks:                                 # mocks ja trazem cstdio/string
        return ""
    if lang == "c":
        return "#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n"
    return "#include <cstdio>\n#include <cstdlib>\n#include <cstring>\n"


def define_block(defines):
    """Converte ['CORE_DEBUG_LEVEL=3', 'FOO'] em linhas #define (vao antes dos mocks)."""
    if not defines:
        return ""
    linhas = []
    for d in defines:
        d = str(d).strip()
        if "=" in d:
            nome, val = d.split("=", 1)
            linhas.append(f"#define {nome.strip()} {val.strip()}")
        else:
            linhas.append(f"#define {d}")
    return "\n".join(linhas) + "\n"


def build_question_source(mock_paths, answer_code, qtype, testcode, defines=None):
    """Monta o fonte de UM caso, no modelo do CodeRunner:
       function -> answer + main{ testcode; } ; program -> answer (tem seu main).
       `defines` entram ANTES dos mocks (ex.: CORE_DEBUG_LEVEL para o log)."""
    nomes = [Path(m).name for m in mock_paths]
    lang = lang_de(qtype, mock_paths)
    partes = [_strip_includes(Path(m).read_text(encoding="utf-8"), nomes) for m in mock_paths]
    answer = _strip_includes(answer_code, nomes)
    src = define_block(defines) + preamble_de(lang, mock_paths) + "\n".join(partes) + "\n" + answer + "\n"
    if qtype in FUNCTION_TYPES or mock_paths:
        tc = testcode.strip()
        if tc and not tc.endswith(";") and not tc.endswith("}"):
            tc += ";"
        src += f"\nint main(void) {{\n    {tc}\n    return 0;\n}}\n"
    # program types: o answer ja tem main; testcode ignorado
    return src, lang


# ---------- execução via Jobe ----------
def run_jobe(jobe_url, source, stdin, apikey=None, language="cpp"):
    url = jobe_url.rstrip("/") + "/jobe/index.php/restapi/runs"
    body = json.dumps({"run_spec": {
        "language_id": language,
        "sourcecode": source,
        "input": stdin,
    }}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if apikey:
        headers["X-API-KEY"] = apikey
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            r = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"outcome": -1, "stdout": "", "cmpinfo": "",
                "stderr": f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')}"}
    except Exception as e:  # noqa: BLE001
        return {"outcome": -2, "stdout": "", "cmpinfo": "", "stderr": str(e)}
    return {"outcome": r.get("outcome"), "stdout": r.get("stdout", ""),
            "cmpinfo": r.get("cmpinfo", ""), "stderr": r.get("stderr", "")}


def jobe_no_ar(jobe_url, apikey=None):
    url = jobe_url.rstrip("/") + "/jobe/index.php/restapi/languages"
    req = urllib.request.Request(url, method="GET")
    if apikey:
        req.add_header("X-API-KEY", apikey)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True, resp.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def norm(s):
    return "\n".join(line.rstrip() for line in (s or "").rstrip("\n").split("\n"))


def _achar(folder, nomes):
    for n in nomes:
        p = folder / n
        if p.is_file():
            return p
    return None


def _casos_do_resultado(res, i, esperado, passou):
    if res["outcome"] == 11:
        print(f"[{i}] ERRO DE COMPILACAO\n{res['cmpinfo'].strip()}")
        return passou
    if res["outcome"] != OK:
        print(f"[{i}] FALHOU (outcome={res['outcome']}) stderr={res['stderr'].strip()}")
        return passou
    if norm(res["stdout"]) == norm(esperado):
        print(f"[{i}] OK")
        return passou + 1
    print(f"[{i}] SAIDA DIFERENTE\n  esperado: {esperado!r}\n  obtido:   {res['stdout']!r}")
    return passou


def roda_modo_pasta(args):
    folder = Path(args.dir)
    if not folder.is_dir():
        print(f"ERRO: pasta nao encontrada: {folder}", file=sys.stderr)
        return 2
    base = folder.name
    meta = {}
    mj = folder / "question.json"
    if mj.is_file():
        meta = json.loads(mj.read_text(encoding="utf-8"))
    qtype = meta.get("type", "c_function")
    # mocks: caminhos relativos a raiz do repo (cwd), como no modo flags
    mocks = meta.get("mocks", [])
    defines = meta.get("defines", [])

    if args.answer:
        answer = Path(args.answer).read_text(encoding="utf-8")
    else:
        sol = _achar(folder, [f"{base}_sol.cpp", "sol.cpp", f"{base}_sol.c", "sol.c"])
        if not sol:
            print(f"ERRO [{base}]: sem solucao de referencia ({base}_sol.cpp ou sol.cpp)", file=sys.stderr)
            return 2
        answer = sol.read_text(encoding="utf-8")

    tf = _achar(folder, [f"{base}_tests.json", "tests.json"])
    if not tf:
        print(f"ERRO [{base}]: sem testes ({base}_tests.json ou tests.json)", file=sys.stderr)
        return 2
    casos = json.loads(tf.read_text(encoding="utf-8"))

    passou = 0
    for i, c in enumerate(casos, 1):
        src, lang = build_question_source(mocks, answer, qtype, c.get("testcode", ""), defines)
        res = run_jobe(args.jobe, src, c.get("stdin", ""), args.apikey, language=lang)
        passou = _casos_do_resultado(res, i, c.get("expected", ""), passou)

    total = len(casos)
    alvo = "referencia" if not args.answer else Path(args.answer).name
    print(f"\n[{base}] {passou}/{total} casos passaram (testando: {alvo}).")
    return 0 if passou == total else 1


def roda_modo_flags(args):
    source = build_source(args.mock, args.student, args.harness)
    casos = json.loads(Path(args.tests).read_text(encoding="utf-8"))
    passou = 0
    for i, c in enumerate(casos, 1):
        res = run_jobe(args.jobe, source, c.get("input", ""), args.apikey, language="cpp")
        passou = _casos_do_resultado(res, i, c.get("expected", ""), passou)
    total = len(casos)
    print(f"\n{passou}/{total} casos passaram.")
    return 0 if passou == total else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Testa codigo no sandbox Jobe (Docker).")
    ap.add_argument("dir", nargs="?", help="pasta da questao (modo pasta), ex.: sqr")
    ap.add_argument("--answer", help="modo pasta: entrega do aluno a testar (em vez da referencia)")
    # modo flags (legado)
    ap.add_argument("--mock", action="append", help="modo flags: header mock (repetivel)")
    ap.add_argument("--student", help="modo flags: codigo do aluno (.cpp)")
    ap.add_argument("--harness", help="modo flags: harness/driver (.cpp)")
    ap.add_argument("--tests", help="modo flags: tests.json [{input, expected}]")
    # comum
    ap.add_argument("--jobe", default=DEFAULT_JOBE, help=f"URL do Jobe (default: {DEFAULT_JOBE})")
    ap.add_argument("--apikey", help="X-API-KEY do Jobe, se exigido")
    args = ap.parse_args(argv)

    modo_flags = any([args.mock, args.student, args.harness, args.tests])
    if args.dir and modo_flags:
        ap.error("use o modo PASTA (positional) OU o modo FLAGS (--mock/--student/...), nao os dois")
    if not args.dir and not modo_flags:
        ap.error("informe a pasta da questao (ex.: jobe_test.py sqr) ou use o modo flags")
    if modo_flags and not (args.mock and args.student and args.harness and args.tests):
        ap.error("modo flags exige --mock, --student, --harness e --tests")

    ok, detalhe = jobe_no_ar(args.jobe, args.apikey)
    if not ok:
        print(f"ERRO: nao consegui falar com o Jobe em {args.jobe}\n  {detalhe}\n\n"
              "Suba um Jobe local com Docker e tente de novo:\n"
              "  docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest\n"
              "  (ja existe? inicie com: docker start jobe)",
              file=sys.stderr)
        return 2

    return roda_modo_pasta(args) if args.dir else roda_modo_flags(args)


if __name__ == "__main__":
    raise SystemExit(main())
