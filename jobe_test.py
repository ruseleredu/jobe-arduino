#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jobe_test.py — testa codigo estilo Arduino (PlatformIO) SEM Moodle, no sandbox Jobe.

Monta um unico fonte C++ = mock(s) + codigo do aluno (sem os #include dos mocks)
+ harness, e executa no Jobe (POST /jobe/index.php/restapi/runs).

Cada caso de teste fornece a entrada (stdin) e a saida esperada (stdout).
A funcao/sketch passa quando outcome == 15 (OK) e o stdout bate.

Pre-requisito: um Jobe rodando. Via Docker:
  docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest

Uso (--jobe tem default http://localhost:4000):
  python jobe_test.py --mock arduino-mock/Arduino.h \\
      --student exemplos/hello_sol.cpp --harness harness/driver_sketch.cpp \\
      --tests exemplos/hello_tests.json

  # varios mocks (ex.: exemplos MQTT):
  python jobe_test.py \\
      --mock arduino-mock/Arduino.h --mock arduino-mock/WiFi.h --mock arduino-mock/PubSubClient.h \\
      --student exemplos/callback_sol.cpp --harness harness/harness_callback.cpp \\
      --tests exemplos/callback_tests.json

  # Jobe em outro host/porta, ou com API key:
  python jobe_test.py --jobe http://192.168.0.10:4000 --apikey SUA-CHAVE ...

tests.json:
  [ {"input": "4\\n", "expected": "1\\n"},
    {"input": "7\\n", "expected": "0\\n"} ]
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


def _strip_includes(text, nomes):
    """Remove os #include dos headers mockados (angle ou quote)."""
    alt = "|".join(re.escape(n) for n in nomes)
    pat = re.compile(r'^\s*#\s*include\s*[<"]\s*(' + alt + r')\s*[>"]\s*$', re.M)
    return pat.sub("// (include de mock removido)", text)


def build_source(mock_paths, student_path, harness_path):
    """Monta UM fonte: mocks (na ordem dada) + codigo do aluno + harness.
    Os includes dos proprios mocks (Arduino.h, WiFi.h, PubSubClient.h) sao
    removidos, pois tudo vira um unico arquivo de traducao."""
    nomes = [Path(m).name for m in mock_paths]
    partes = []
    for m in mock_paths:
        partes.append(_strip_includes(Path(m).read_text(encoding="utf-8"), nomes))
    aluno = _strip_includes(Path(student_path).read_text(encoding="utf-8"), nomes)
    harness = Path(harness_path).read_text(encoding="utf-8")
    return ("\n".join(partes) + "\n// ===== codigo do aluno =====\n" + aluno
            + "\n// ===== harness =====\n" + harness + "\n")


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
    except urllib.error.URLError as e:
        return {"outcome": -2, "stdout": "", "cmpinfo": "", "stderr": str(e.reason)}
    except Exception as e:  # noqa: BLE001
        return {"outcome": -2, "stdout": "", "cmpinfo": "", "stderr": str(e)}
    return {"outcome": r.get("outcome"), "stdout": r.get("stdout", ""),
            "cmpinfo": r.get("cmpinfo", ""), "stderr": r.get("stderr", "")}


def jobe_no_ar(jobe_url, apikey=None):
    """Confere se o Jobe responde (GET languages). Retorna (ok, detalhe)."""
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
    # comparacao tolerante a espacos no fim das linhas e newline final
    return "\n".join(line.rstrip() for line in (s or "").rstrip("\n").split("\n"))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Testa codigo Arduino no sandbox Jobe (Docker).")
    ap.add_argument("--mock", required=True, action="append",
                    help="header(s) mock; repita para varios (ex.: --mock Arduino.h --mock PubSubClient.h)")
    ap.add_argument("--student", required=True, help="codigo do aluno (.cpp)")
    ap.add_argument("--harness", required=True, help="harness/driver (.cpp)")
    ap.add_argument("--tests", required=True, help="tests.json [{input, expected}]")
    ap.add_argument("--jobe", default=DEFAULT_JOBE,
                    help=f"URL do Jobe (default: {DEFAULT_JOBE})")
    ap.add_argument("--apikey", help="X-API-KEY do Jobe, se exigido")
    args = ap.parse_args(argv)

    # checa o Jobe antes de rodar; mensagem clara se estiver fora do ar
    ok, detalhe = jobe_no_ar(args.jobe, args.apikey)
    if not ok:
        print(f"ERRO: nao consegui falar com o Jobe em {args.jobe}\n  {detalhe}\n\n"
              "Suba um Jobe local com Docker e tente de novo:\n"
              "  docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest\n"
              "  (ja existe? inicie com: docker start jobe)",
              file=sys.stderr)
        return 2

    source = build_source(args.mock, args.student, args.harness)
    casos = json.loads(Path(args.tests).read_text(encoding="utf-8"))

    passou = 0
    for i, caso in enumerate(casos, 1):
        entrada = caso.get("input", "")
        esperado = caso.get("expected", "")
        res = run_jobe(args.jobe, source, entrada, args.apikey)

        if res["outcome"] == 11:
            print(f"[{i}] ERRO DE COMPILACAO\n{res['cmpinfo'].strip()}")
            continue
        if res["outcome"] != OK:
            print(f"[{i}] FALHOU (outcome={res['outcome']}) stderr={res['stderr'].strip()}")
            continue
        if norm(res["stdout"]) == norm(esperado):
            passou += 1
            print(f"[{i}] OK")
        else:
            print(f"[{i}] SAIDA DIFERENTE\n  esperado: {esperado!r}\n  obtido:   {res['stdout']!r}")

    total = len(casos)
    print(f"\n{passou}/{total} casos passaram.")
    return 0 if passou == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
