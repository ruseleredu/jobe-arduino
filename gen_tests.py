#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_tests.py — gera <base>_tests.json a partir de ENTRADAS de teste, calculando
o 'expected' ao rodar a SOLUCAO DE REFERENCIA no Jobe.

Objetivo: o professor fornece questiontext.html, sol.cpp, answerpreload.cpp e um
arquivo simples de casos; o 'expected' (parte tediosa e propensa a erro) e
preenchido automaticamente pela saida da referencia.

Fonte dos casos (procurada na pasta, nesta ordem):
  <base>_cases.txt / cases.txt   — um caso por linha (texto)
  <base>_cases.json / cases.json — lista de objetos (sem 'expected')

Formato do cases.txt (um caso por linha; '#' = comentario; linhas vazias ignoradas):
  - A linha e o 'testcode' (o trecho que chama a funcao e imprime), OU — se
    question.json define "call" com '{}' — a linha e apenas o(s) argumento(s).
  - Marcadores no fim da linha: @example (vira exemplo, SHOW) e @hide (display HIDE).

Exemplos:
  # com "call": "printf(\\"%d\\\\n\\", sqr({}))" no question.json
  -11   @example
  9     @example
  -1000
  0
  8     @hide

  # sem "call" (testcode completo por linha)
  printf("%d\\n", sqr(9))   @example

cases.json (quando precisa de stdin ou mais controle):
  [ { "testcode": "...", "stdin": "", "example": true, "display": "SHOW" },
    { "args": "3, 7", "example": false } ]      // 'args' usa o template "call"

Uso:
  python gen_tests.py questions/sqr                 # grava questions/sqr/sqr_tests.json
  python gen_tests.py questions/*                   # varias (glob do shell)
  python gen_tests.py questions --all               # todas as subpastas de questions/
  python gen_tests.py questions/sqr --force         # sobrescreve tests.json existente
  # Jobe: --jobe http://localhost:4000 (default), --apikey SE exigido
"""
import argparse
import json
import os
import sys
from pathlib import Path

DEFAULT_JOBE = os.environ.get("JOBE_URL", "http://localhost:4000")

try:
    import jobe_test as jt
except Exception as e:  # noqa: BLE001
    print(f"ERRO: preciso de jobe_test.py ao lado deste script ({e})", file=sys.stderr)
    raise SystemExit(2)

MARCADORES = {"@example", "@hide", "@show"}


TOOLKIT_HOME = os.environ.get("JOBE_ARDUINO_HOME") or os.path.dirname(os.path.abspath(__file__))


def _resolve_mock(folder, rel):
    for c in (Path(rel), folder.parent.parent / rel, folder.parent / rel, Path(TOOLKIT_HOME) / rel):
        if c.is_file():
            return str(c)
    raise SystemExit(f"ERRO: mock nao encontrado: {rel}")


def _achar(folder, nomes):
    for n in nomes:
        p = folder / n
        if p.is_file():
            return p
    return None


def _mdl(folder):
    """Pasta dos arquivos da questao: <folder>/mdl se existir, senao <folder>."""
    m = Path(folder) / "mdl"
    return m if m.is_dir() else Path(folder)


def parse_linha_txt(linha, call_tpl):
    """Converte uma linha do cases.txt em dict {testcode, example, display}."""
    toks = linha.split()
    marcas = set()
    while toks and toks[-1] in MARCADORES:
        marcas.add(toks.pop())
    corpo = linha
    # remove os marcadores do fim preservando o corpo original (com espacos internos)
    for m in MARCADORES:
        if corpo.rstrip().endswith(m):
            corpo = corpo.rstrip()[: -len(m)]
    corpo = corpo.strip()
    testcode = call_tpl.replace("{}", corpo) if call_tpl else corpo
    return {
        "testcode": testcode,
        "example": "@example" in marcas,
        "display": "HIDE" if "@hide" in marcas else "SHOW",
    }


def carregar_casos(folder, base, call_tpl):
    txt = _achar(folder, [f"{base}_cases.txt", "cases.txt"])
    if txt:
        casos = []
        for linha in txt.read_text(encoding="utf-8").splitlines():
            s = linha.strip()
            if not s or s.startswith("#"):
                continue
            casos.append(parse_linha_txt(linha, call_tpl))
        return casos
    js = _achar(folder, [f"{base}_cases.json", "cases.json"])
    if js:
        casos = []
        for c in json.loads(js.read_text(encoding="utf-8")):
            tc = c.get("testcode")
            if tc is None and "args" in c:
                tc = (call_tpl or "{}").replace("{}", str(c["args"]))
            casos.append({
                "testcode": tc or "",
                "stdin": c.get("stdin", ""),
                "example": bool(c.get("example", False)),
                "display": c.get("display", "SHOW"),
            })
        return casos
    return None


def gerar_para(folder, jobe, apikey, force):
    folder = Path(folder)
    base = folder.name
    qdir = _mdl(folder)          # arquivos da questao em <folder>/mdl (ou <folder>)
    meta = {}
    mj = qdir / "question.json"
    if mj.is_file():
        meta = json.loads(mj.read_text(encoding="utf-8"))
    qtype = meta.get("type", "c_function")
    call_tpl = meta.get("call", "")
    mocks = [_resolve_mock(folder, m) for m in meta.get("mocks", [])]
    defines = meta.get("defines", [])

    sol = _achar(qdir, [f"{base}_sol.cpp", "sol.cpp", f"{base}_sol.c", "sol.c"])
    if not sol:
        print(f"ERRO [{base}]: sem solucao de referencia ({base}_sol.cpp ou sol.cpp)", file=sys.stderr)
        return False
    answer = sol.read_text(encoding="utf-8")

    casos = carregar_casos(qdir, base, call_tpl)
    if casos is None:
        print(f"ERRO [{base}]: sem arquivo de casos ({base}_cases.txt / cases.txt / cases.json)", file=sys.stderr)
        return False

    destino = qdir / f"{base}_tests.json"
    if destino.exists() and not force:
        print(f"ERRO [{base}]: {destino.name} ja existe (use --force para sobrescrever)", file=sys.stderr)
        return False

    tests = []
    for i, c in enumerate(casos, 1):
        src, lang = jt.build_question_source(mocks, answer, qtype, c["testcode"], defines)
        res = jt.run_jobe(jobe, src, c.get("stdin", ""), apikey, language=lang)
        if res["outcome"] == 11:
            print(f"ERRO [{base}] caso {i}: a REFERENCIA nao compila:\n{res['cmpinfo'].strip()}", file=sys.stderr)
            return False
        if res["outcome"] != jt.OK:
            print(f"ERRO [{base}] caso {i}: outcome={res['outcome']} stderr={res['stderr'].strip()}", file=sys.stderr)
            return False
        expected = (res["stdout"] or "").rstrip("\n")
        entrada = {"testcode": c["testcode"]}
        if c.get("stdin"):
            entrada["stdin"] = c["stdin"]
        entrada["expected"] = expected
        if c.get("example"):
            entrada["example"] = True
        if c.get("display", "SHOW") != "SHOW":
            entrada["display"] = c["display"]
        tests.append(entrada)

    destino.write_text(json.dumps(tests, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ex = sum(1 for t in tests if t.get("example"))
    print(f"gravado: {destino}  ({len(tests)} casos, {ex} exemplo(s))", file=sys.stderr)
    return True


def eh_pasta_questao(p):
    for d in (p, p / "mdl"):
        if (d / "question.json").is_file():
            return True
        for n in (f"{p.name}_sol.cpp", "sol.cpp", f"{p.name}_sol.c", "sol.c"):
            if (d / n).is_file():
                return True
    return False


def expandir(paths, usar_all):
    """Pasta-questao vira ela mesma; pasta-contêiner vira suas subpastas-questao.
    --all forca tratar o arg como contêiner mesmo que ele proprio pareca questao."""
    out = []
    for f in paths:
        p = Path(f)
        if not p.is_dir():
            print(f"aviso: ignorando '{f}' (nao e pasta)", file=sys.stderr)
            continue
        if eh_pasta_questao(p) and not usar_all:
            out.append(p)
        else:
            subs = [d for d in sorted(p.iterdir()) if d.is_dir() and eh_pasta_questao(d)]
            if subs:
                out.extend(subs)
            elif eh_pasta_questao(p):
                out.append(p)
            else:
                print(f"aviso: '{f}' nao e questao nem contem questoes", file=sys.stderr)
    vistos, unicas = set(), []
    for d in out:
        r = d.resolve()
        if r not in vistos:
            vistos.add(r); unicas.append(d)
    return unicas


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gera tests.json rodando a referencia no Jobe.")
    ap.add_argument("folders", nargs="+", help="pasta(s) de questao ou contêiner")
    ap.add_argument("--all", action="store_true", help="trata cada arg como contêiner (usa subpastas)")
    ap.add_argument("--force", action="store_true", help="sobrescreve <base>_tests.json existente")
    ap.add_argument("--jobe", default=DEFAULT_JOBE, help=f"URL do Jobe (default: {DEFAULT_JOBE}; ou env JOBE_URL)")
    ap.add_argument("--apikey", help="X-API-KEY do Jobe, se exigido")
    args = ap.parse_args(argv)

    pastas = expandir(args.folders, args.all)
    if not pastas:
        ap.error("nenhuma pasta de questao encontrada")

    ok, detalhe = jt.jobe_no_ar(args.jobe, args.apikey)
    if not ok:
        print(f"ERRO: Jobe indisponivel em {args.jobe}: {detalhe}\n"
              "  docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest", file=sys.stderr)
        return 2

    falhou = 0
    for p in pastas:
        if not gerar_para(p, args.jobe, args.apikey, args.force):
            falhou += 1
    return 1 if falhou else 0


if __name__ == "__main__":
    raise SystemExit(main())
