#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_moodle_xml.py — gera XML CodeRunner (Moodle) a partir de pasta(s) de questao.

Convencao de pasta (nome da pasta = base da questao, ex.: sqr):
  sqr/
    question.json       # metadados (nome, tipo, nota, regime de penalidade, ...)
    questiontext.html   # enunciado (HTML) -> <questiontext>
    answerpreload.cpp   # base para o aluno comecar -> <answerpreload> (opcional)
    sqr_sol.cpp         # solucao de referencia -> <answer>   (fallback: sol.cpp)
    sqr_tests.json      # casos de teste -> <testcases>        (fallback: tests.json)
    generalfeedback.html# opcional -> <generalfeedback>

tests.json (alinhado ao CodeRunner):
  [ { "testcode": "printf(\\"%d\\\\n\\", sqr(9))",
      "stdin": "", "expected": "81",
      "example": true, "display": "SHOW", "mark": 1.0 } ]

Uso:
  python gen_moodle_xml.py sqr                      # uma questao -> stdout
  python gen_moodle_xml.py sqr ehpar -o banco.xml   # varias -> um arquivo .xml
  python gen_moodle_xml.py questions/* -o banco.xml # glob do shell
"""
import argparse
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

# defaults por campo da questao (espelham o export do CodeRunner)
Q_DEFAULTS = {
    "type": "c_function",
    "defaultgrade": 1,
    "penalty": 0,
    "hidden": 0,
    "allornothing": 1,
    "precheck": 0,
    "hidecheck": 0,
    "showsource": 0,
    "answerboxlines": 8,
    "answerboxcolumns": 60,
    "penaltyregime": "0, 10, 20, ...",
    "validateonsave": 1,
    "displayfeedback": 0,
}


def cdata(s):
    """Envolve em CDATA, fechando com seguranca se houver ']]>' no conteudo."""
    s = s or ""
    return "<![CDATA[" + s.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def ler(p, default=""):
    return p.read_text(encoding="utf-8") if p.is_file() else default


# Headers mockados cujos #include devem ser removidos ao embutir em globalextra.
MOCK_NAMES = ["Arduino.h", "WiFi.h", "PubSubClient.h"]


def _strip_mock_includes(text):
    alt = "|".join(re.escape(n) for n in MOCK_NAMES)
    pat = re.compile(r'^\s*#\s*include\s*[<"]\s*(' + alt + r')\s*[>"]\s*$', re.M)
    return pat.sub("// (include de mock removido)", text)


def _resolve_mock(folder, rel):
    """Resolve o caminho do mock: tenta cwd, depois a raiz do repo (acima de questions/)."""
    cand = [Path(rel), folder.parent.parent / rel, folder.parent / rel]
    for c in cand:
        if c.is_file():
            return c
    raise SystemExit(f"ERRO: mock nao encontrado: {rel} (procurei em {[str(c) for c in cand]})")


# Template C++ determinístico para questões com mocks Arduino.
# Compila: includes + mocks (globalextra) + resposta do aluno + main por caso de teste.
MOCK_TEMPLATE = """#include <cstdio>
#include <cstdlib>
#include <cstring>

{{ QUESTION.globalextra }}

{{ STUDENT_ANSWER }}

int main() {
    {{ TEST.testcode }};
    return 0;
}
"""


def achar(folder, base, sufixos):
    """Procura <base><sufixo> e depois <generico><sufixo>."""
    for nome in sufixos:
        p = folder / nome
        if p.is_file():
            return p
    return None


def carrega_questao(folder):
    folder = Path(folder)
    base = folder.name
    meta = {}
    mj = folder / "question.json"
    if mj.is_file():
        meta = json.loads(mj.read_text(encoding="utf-8"))
    q = dict(Q_DEFAULTS)
    q.update(meta)
    q.setdefault("name", base)

    q["questiontext"] = ler(folder / "questiontext.html", f"<p>{escape(base)}</p>")
    q["generalfeedback"] = ler(folder / "generalfeedback.html", "")
    q["answerpreload"] = ler(achar(folder, base, ["answerpreload.cpp", "answerpreload.c",
                                                   "answerpreload.py", "answerpreload.txt"]) or Path("/nonexistent"), "")

    sol = achar(folder, base, [f"{base}_sol.cpp", "sol.cpp", f"{base}_sol.c", "sol.c",
                               f"{base}_sol.py", "sol.py"])
    if not sol:
        raise SystemExit(f"ERRO [{base}]: nao achei a solucao de referencia (ex.: {base}_sol.cpp ou sol.cpp)")
    q["answer"] = sol.read_text(encoding="utf-8")

    tf = achar(folder, base, [f"{base}_tests.json", "tests.json"])
    if not tf:
        raise SystemExit(f"ERRO [{base}]: nao achei os testes (ex.: {base}_tests.json ou tests.json)")
    q["testcases"] = json.loads(tf.read_text(encoding="utf-8"))

    # guarda infos usadas pela validacao (--validate)
    q["base"] = base
    mocks = meta.get("mocks", [])
    defines = meta.get("defines", [])
    q["mock_paths"] = [str(_resolve_mock(folder, m)) for m in mocks] if mocks else []
    q["defines"] = defines
    q["answer_raw"] = q["answer"]

    # bloco de #define (ex.: CORE_DEBUG_LEVEL para o log) vai ANTES dos mocks
    dblk = ""
    if defines:
        linhas = []
        for d in defines:
            d = str(d).strip()
            if "=" in d:
                nome, val = d.split("=", 1)
                linhas.append(f"#define {nome.strip()} {val.strip()}")
            else:
                linhas.append(f"#define {d}")
        dblk = "\n".join(linhas) + "\n"

    # Questoes com mocks Arduino: embute defines + mocks em globalextra + template C++.
    if mocks:
        partes = [_strip_mock_includes(_resolve_mock(folder, m).read_text(encoding="utf-8")) for m in mocks]
        q["globalextra"] = dblk + "\n".join(partes)
        q["template"] = MOCK_TEMPLATE
        # a resposta e a base do aluno nao devem reincluir os mocks
        q["answer"] = _strip_mock_includes(q["answer"])
        q["answerpreload"] = _strip_mock_includes(q["answerpreload"])
    else:
        q.setdefault("globalextra", dblk)
        q.setdefault("template", "")
    return q


def render_testcase(tc):
    testtype = int(tc.get("testtype", 0))
    useasexample = 1 if tc.get("example", False) else 0
    hiderestiffail = 1 if tc.get("hiderestiffail", False) else 0
    mark = float(tc.get("mark", 1.0))
    display = tc.get("display", "SHOW")
    testcode = tc.get("testcode", "")
    stdin = tc.get("stdin", "")
    expected = tc.get("expected", "")
    extra = tc.get("extra", "")
    return f"""      <testcase testtype="{testtype}" useasexample="{useasexample}" hiderestiffail="{hiderestiffail}" mark="{mark:.7f}" >
      <testcode>
                <text>{cdata(testcode)}</text>
      </testcode>
      <stdin>
                <text>{escape(stdin)}</text>
      </stdin>
      <expected>
                <text>{escape(expected)}</text>
      </expected>
      <extra>
                <text>{escape(extra)}</text>
      </extra>
      <display>
                <text>{escape(display)}</text>
      </display>
    </testcase>"""


def render_question(q):
    tcs = "\n".join(render_testcase(tc) for tc in q["testcases"])
    return f"""  <question type="coderunner">
    <name>
      <text>{escape(str(q["name"]))}</text>
    </name>
    <questiontext format="html">
      <text>{cdata(q["questiontext"])}</text>
    </questiontext>
    <generalfeedback format="html">
      <text>{cdata(q["generalfeedback"])}</text>
    </generalfeedback>
    <defaultgrade>{q["defaultgrade"]}</defaultgrade>
    <penalty>{q["penalty"]}</penalty>
    <hidden>{q["hidden"]}</hidden>
    <idnumber></idnumber>
    <coderunnertype>{escape(str(q["type"]))}</coderunnertype>
    <prototypetype>0</prototypetype>
    <allornothing>{q["allornothing"]}</allornothing>
    <penaltyregime>{escape(str(q["penaltyregime"]))}</penaltyregime>
    <precheck>{q["precheck"]}</precheck>
    <hidecheck>{q["hidecheck"]}</hidecheck>
    <showsource>{q["showsource"]}</showsource>
    <answerboxlines>{q["answerboxlines"]}</answerboxlines>
    <answerboxcolumns>{q["answerboxcolumns"]}</answerboxcolumns>
    <answerpreload>{escape(q["answerpreload"])}</answerpreload>
    <globalextra>{escape(q.get("globalextra", ""))}</globalextra>
    <useace></useace>
    <resultcolumns></resultcolumns>
    <template>{escape(q.get("template", ""))}</template>
    <iscombinatortemplate>{"0" if q.get("template") else ""}</iscombinatortemplate>
    <allowmultiplestdins></allowmultiplestdins>
    <answer>{escape(q["answer"])}</answer>
    <validateonsave>{q["validateonsave"]}</validateonsave>
    <testsplitterre></testsplitterre>
    <language></language>
    <acelang></acelang>
    <sandbox></sandbox>
    <grader></grader>
    <cputimelimitsecs></cputimelimitsecs>
    <memlimitmb></memlimitmb>
    <sandboxparams></sandboxparams>
    <templateparams></templateparams>
    <hoisttemplateparams>0</hoisttemplateparams>
    <extractcodefromjson>1</extractcodefromjson>
    <templateparamslang>twig</templateparamslang>
    <templateparamsevalpertry>0</templateparamsevalpertry>
    <templateparamsevald></templateparamsevald>
    <twigall>0</twigall>
    <uiplugin></uiplugin>
    <uiparameters></uiparameters>
    <attachments>0</attachments>
    <attachmentsrequired>0</attachmentsrequired>
    <maxfilesize>0</maxfilesize>
    <filenamesregex></filenamesregex>
    <filenamesexplain></filenamesexplain>
    <displayfeedback>{q["displayfeedback"]}</displayfeedback>
    <giveupallowed>0</giveupallowed>
    <prototypeextra></prototypeextra>
    <testcases>
{tcs}
    </testcases>
  </question>"""


def render_quiz(questoes):
    corpo = "\n\n".join(render_question(q) for q in questoes)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<quiz>
{corpo}

</quiz>
"""


def eh_pasta_questao(p):
    """True se p parece uma pasta de questao (tem question.json ou uma solucao)."""
    if (p / "question.json").is_file():
        return True
    base = p.name
    for n in (f"{base}_sol.cpp", "sol.cpp", f"{base}_sol.c", "sol.c",
              f"{base}_sol.py", "sol.py"):
        if (p / n).is_file():
            return True
    return False


def expandir_pastas(paths):
    """Cada arg: uma pasta-questao vira ela mesma; uma pasta-contêiner vira suas
    subpastas-questao (ordenadas). Permite `questions` ou `questions/*`."""
    out = []
    for f in paths:
        p = Path(f)
        if not p.is_dir():
            print(f"aviso: ignorando '{f}' (nao e pasta)", file=sys.stderr)
            continue
        if eh_pasta_questao(p):
            out.append(p)
        else:
            subs = [d for d in sorted(p.iterdir()) if d.is_dir() and eh_pasta_questao(d)]
            if subs:
                out.extend(subs)
            else:
                print(f"aviso: '{f}' nao e questao nem contem questoes", file=sys.stderr)
    # remove duplicatas preservando a ordem
    vistos, unicas = set(), []
    for d in out:
        r = d.resolve()
        if r not in vistos:
            vistos.add(r); unicas.append(d)
    return unicas


def validar(questoes, jobe_url, apikey):
    """Roda a solucao de referencia de cada questao no Jobe. Retorna (ok, relatorio)."""
    try:
        import jobe_test as jt
    except Exception as e:  # noqa: BLE001
        print(f"ERRO: --validate precisa de jobe_test.py ao lado deste script ({e})", file=sys.stderr)
        return False, []

    ok, detalhe = jt.jobe_no_ar(jobe_url, apikey)
    if not ok:
        print(f"ERRO: Jobe indisponivel em {jobe_url}: {detalhe}\n"
              "  docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest", file=sys.stderr)
        return False, []

    relatorio, tudo_ok = [], True
    for q in questoes:
        qtype = q.get("type", "c_function")
        mocks = q.get("mock_paths", [])
        answer = q.get("answer_raw", q.get("answer", ""))
        casos = q.get("testcases", [])
        falhas = []
        defines = q.get("defines", [])
        for i, c in enumerate(casos, 1):
            src, lang = jt.build_question_source(mocks, answer, qtype, c.get("testcode", ""), defines)
            res = jt.run_jobe(jobe_url, src, c.get("stdin", ""), apikey, language=lang)
            if res["outcome"] == 11:
                falhas.append(f"TC{i}: erro de compilacao")
            elif res["outcome"] != jt.OK:
                falhas.append(f"TC{i}: outcome={res['outcome']}")
            elif jt.norm(res["stdout"]) != jt.norm(c.get("expected", "")):
                falhas.append(f"TC{i}: saida != esperado ({res['stdout']!r} vs {c.get('expected','')!r})")
        if falhas:
            tudo_ok = False
            relatorio.append(f"  [X] {q['base']} ({len(casos)-len(falhas)}/{len(casos)}): " + "; ".join(falhas))
        else:
            relatorio.append(f"  [ok] {q['base']} ({len(casos)}/{len(casos)})")
    return tudo_ok, relatorio


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gera XML CodeRunner (Moodle) de pasta(s) de questao.")
    ap.add_argument("folders", nargs="+",
                    help="pasta(s) de questao ou contêiner (ex.: questions/sqr, ou questions, ou questions/*)")
    ap.add_argument("-o", "--output", help="arquivo .xml de saida (default: stdout)")
    ap.add_argument("--validate", action="store_true",
                    help="roda a solucao de referencia no Jobe antes de gerar; falha se algum teste nao passar")
    ap.add_argument("--jobe", default="http://localhost:4000", help="URL do Jobe (para --validate)")
    ap.add_argument("--apikey", help="X-API-KEY do Jobe (para --validate)")
    args = ap.parse_args(argv)

    pastas = expandir_pastas(args.folders)
    if not pastas:
        ap.error("nenhuma pasta de questao valida encontrada")
    questoes = [carrega_questao(p) for p in pastas]

    if args.validate:
        tudo_ok, relatorio = validar(questoes, args.jobe, args.apikey)
        print("Validacao no Jobe:", file=sys.stderr)
        for linha in relatorio:
            print(linha, file=sys.stderr)
        if not tudo_ok:
            print("\nXML NAO gerado: corrija as questoes acima.", file=sys.stderr)
            return 1

    xml = render_quiz(questoes)
    if args.output:
        Path(args.output).write_text(xml, encoding="utf-8")
        print(f"gravado: {args.output}  ({len(questoes)} questao(oes))", file=sys.stderr)
    else:
        sys.stdout.write(xml)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
