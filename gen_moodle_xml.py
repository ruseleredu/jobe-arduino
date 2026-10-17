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
import os
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

DEFAULT_JOBE = os.environ.get("JOBE_URL", "http://localhost:4000")

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
MOCK_NAMES = ["Arduino.h", "WiFi.h", "PubSubClient.h", "esp32-hal-log.h", "DHT.h", "Ticker.h"]


def _strip_mock_includes(text):
    alt = "|".join(re.escape(n) for n in MOCK_NAMES)
    pat = re.compile(r'^\s*#\s*include\s*[<"]\s*(' + alt + r')\s*[>"]\s*$', re.M)
    return pat.sub("// (include de mock removido)", text)


TOOLKIT_HOME = os.environ.get("JOBE_ARDUINO_HOME") or os.path.dirname(os.path.abspath(__file__))


def _resolve_mock(folder, rel):
    """Resolve o mock: cwd, raiz do repo (acima de questions/), e o TOOLKIT_HOME
    (ex.: baked na imagem Docker, para repos que so tem questoes)."""
    cand = [Path(rel), folder.parent.parent / rel, folder.parent / rel, Path(TOOLKIT_HOME) / rel]
    for c in cand:
        if c.is_file():
            return c
    raise SystemExit(f"ERRO: mock nao encontrado: {rel} (procurei em {[str(c) for c in cand]})")


def _mdl(folder):
    """Pasta dos arquivos da questao: <folder>/mdl se existir, senao <folder>."""
    m = Path(folder) / "mdl"
    return m if m.is_dir() else Path(folder)


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

# Template para SKETCH Arduino (setup/loop sem main): o harness chama setup() uma vez.
# A resposta do aluno define setup()/loop(); nao ha testcode (a saida inteira e checada).
ARDUINO_TEMPLATE = """#include <cstdio>
#include <cstdlib>
#include <cstring>

{{ QUESTION.globalextra }}

{{ STUDENT_ANSWER }}

int main() {
    setup();
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


def _lexer_por_nome(nome, code_lang=None):
    """Escolhe um lexer Pygments pela extensao do arquivo ou por code_lang."""
    from pygments.lexers import CLexer, CppLexer, PythonLexer, get_lexer_by_name
    if code_lang:
        try:
            return get_lexer_by_name(code_lang)
        except Exception:  # noqa: BLE001
            pass
    ext = Path(nome).suffix.lower()
    if ext == ".c":
        return CLexer()
    if ext in (".py",):
        return PythonLexer()
    return CppLexer()  # .cpp/.ino/.h e default


def highlight_html(codigo, nome, code_lang=None):
    """Destaca o codigo com Pygments em HTML com estilos INLINE (sobrevive ao
    filtro do Moodle, sem CSS externo). Se o Pygments faltar, usa <pre> simples."""
    try:
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
    except Exception:  # noqa: BLE001
        return "<pre><code>" + escape(codigo) + "</code></pre>"
    lexer = _lexer_por_nome(nome, code_lang)
    fmt = HtmlFormatter(noclasses=True, nowrap=False, style="friendly")
    bloco = highlight(codigo, lexer, fmt)  # <div class="highlight"><pre>...styles inline...</pre></div>
    # moldura leve para contraste em qualquer tema do Moodle
    return ('<div style="border:1px solid #ddd;border-radius:6px;padding:6px 10px;'
            'overflow:auto;">' + bloco + "</div>")


def _achar_codigo(folder, base):
    return achar(folder, base, [f"{base}_code.cpp", f"{base}_sol.cpp", "code.cpp", "sol.cpp",
                                f"{base}_code.c", "code.c", f"{base}_code.ino", "code.ino",
                                f"{base}_code.py", "code.py"])


def _cloze_escape(s):
    """Escapa caracteres de controle do Cloze para uso DENTRO de um campo embutido."""
    for ch in ["\\", "{", "}", "~", "#", "=", "/"]:
        s = s.replace(ch, "\\" + ch)
    return s


def _embute_codigo(html, qdir, base, meta):
    """Substitui {{CODE}} por codigo destacado (Pygments)."""
    if "{{CODE}}" not in html:
        return html
    cf = _achar_codigo(qdir, base)
    if cf:
        bloco = highlight_html(cf.read_text(encoding="utf-8").rstrip("\n"), cf.name, meta.get("code_lang"))
    else:
        bloco = "<pre><code>// (codigo nao encontrado)</code></pre>"
    return html.replace("{{CODE}}", bloco)


def _embute_saida(html, qdir, folder, base, meta, jobe, apikey):
    """Substitui {{OUTPUT}} (valor p/ campo Cloze) e {{OUTPUT_BLOCK}} (bloco <pre>)
    pela saida do codigo exibido, computada rodando-o no Jobe.
    qdir: pasta dos arquivos da questao (<folder>/mdl); folder: raiz para achar mocks."""
    if "{{OUTPUT}}" not in html and "{{OUTPUT_BLOCK}}" not in html:
        return html
    import jobe_test as jt
    cf = _achar_codigo(qdir, base)
    if not cf:
        raise SystemExit(f"ERRO [{base}]: {{OUTPUT}} pede o codigo exibido ({base}_code.cpp), nao encontrado")
    ok, det = jt.jobe_no_ar(jobe, apikey)
    if not ok:
        raise SystemExit(f"ERRO [{base}]: {{OUTPUT}} precisa do Jobe em {jobe}: {det}\n"
                         "  docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest")
    mocks = [str(_resolve_mock(folder, m)) for m in meta.get("mocks", [])]
    defines = meta.get("defines", [])
    code_type = meta.get("code_type", "cpp_program")   # programa completo (tem main)
    src, lang = jt.build_question_source(mocks, cf.read_text(encoding="utf-8"), code_type, "", defines)
    res = jt.run_jobe(jobe, src, meta.get("stdin", ""), apikey, language=lang)
    if res["outcome"] != jt.OK:
        raise SystemExit(f"ERRO [{base}]: codigo exibido nao executou (outcome={res['outcome']})\n"
                         f"{res.get('cmpinfo','').strip() or res.get('stderr','').strip()}")
    saida = (res["stdout"] or "").rstrip("\n")
    html = html.replace("{{OUTPUT}}", _cloze_escape(saida))
    html = html.replace("{{OUTPUT_BLOCK}}", "<pre><code>" + escape(saida) + "</code></pre>")
    return html


def carrega_questao(folder, jobe="http://localhost:4000", apikey=None):
    folder = Path(folder)
    base = folder.name
    qdir = _mdl(folder)          # arquivos da questao em <folder>/mdl (ou <folder>)
    meta = {}
    mj = qdir / "question.json"
    if mj.is_file():
        meta = json.loads(mj.read_text(encoding="utf-8"))
    q = dict(Q_DEFAULTS)
    q.update(meta)
    q.setdefault("name", base)

    # ---- SQL (CodeRunner tipo 'sql' / sqlite3): schema em globalextra, consulta = answer ----
    if str(q.get("type", "")).lower() == "sql":
        q["base"] = base
        q["_sql"] = True
        q["questiontext"] = ler(qdir / "questiontext.html", f"<p>{escape(base)}</p>")
        q["generalfeedback"] = ler(qdir / "generalfeedback.html", "")
        q["globalextra"] = ler(achar(qdir, base, ["schema.sql"]) or Path("/nonexistent"), "")
        solq = achar(qdir, base, [f"{base}_sol.sql", "sol.sql"])
        if not solq:
            raise SystemExit(f"ERRO [{base}]: nao achei a consulta de referencia ({base}_sol.sql)")
        q["answer"] = solq.read_text(encoding="utf-8")
        tf = achar(qdir, base, [f"{base}_tests.json", "tests.json"])
        q["testcases"] = json.loads(tf.read_text(encoding="utf-8")) if tf else [{"testcode": "", "expected": ""}]
        q["answerpreload"] = ler(achar(qdir, base, ["answerpreload.sql"]) or Path("/nonexistent"), "")
        q["template"] = ""   # usa o prototipo 'sql' embutido do CodeRunner
        return q

    # ---- Cloze / Embedded Answers (multianswer): analise de codigo ----
    if str(q.get("type", "")).lower() in ("cloze", "multianswer"):
        q["_cloze"] = True
        q["base"] = base
        html = ler(qdir / "questiontext.html", f"<p>{escape(base)}</p>")
        html = _embute_codigo(html, qdir, base, meta)       # {{CODE}} -> Pygments
        html = _embute_saida(html, qdir, folder, base, meta, jobe, apikey)  # {{OUTPUT}}/{{OUTPUT_BLOCK}}
        q["questiontext"] = html
        q["generalfeedback"] = ler(qdir / "generalfeedback.html", "")
        if "penalty" not in meta:
            q["penalty"] = 0.3333333
        return q

    q["questiontext"] = ler(qdir / "questiontext.html", f"<p>{escape(base)}</p>")
    q["generalfeedback"] = ler(qdir / "generalfeedback.html", "")
    q["answerpreload"] = ler(achar(qdir, base, ["answerpreload.cpp", "answerpreload.c",
                                                 "answerpreload.py", "answerpreload.txt"]) or Path("/nonexistent"), "")

    sol = achar(qdir, base, [f"{base}_sol.cpp", "sol.cpp", f"{base}_sol.c", "sol.c",
                             f"{base}_sol.py", "sol.py"])
    if not sol:
        raise SystemExit(f"ERRO [{base}]: nao achei a solucao de referencia (ex.: {base}_sol.cpp ou sol.cpp)")
    q["answer"] = sol.read_text(encoding="utf-8")

    tf = achar(qdir, base, [f"{base}_tests.json", "tests.json"])
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
        # sketch Arduino -> template que chama setup(); demais -> main com testcode
        q["template"] = ARDUINO_TEMPLATE if str(q.get("type", "")).lower() == "arduino" else MOCK_TEMPLATE
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


def render_cloze(q):
    return f"""  <question type="cloze">
    <name>
      <text>{escape(str(q["name"]))}</text>
    </name>
    <questiontext format="html">
      <text>{cdata(q["questiontext"])}</text>
    </questiontext>
    <generalfeedback format="html">
      <text>{cdata(q.get("generalfeedback", ""))}</text>
    </generalfeedback>
    <penalty>{q.get("penalty", 0.3333333)}</penalty>
    <hidden>{q.get("hidden", 0)}</hidden>
    <idnumber></idnumber>
  </question>"""


def render_question(q):
    if q.get("_cloze"):
        return render_cloze(q)
    tcs = "\n".join(render_testcase(tc) for tc in q["testcases"])
    # 'arduino' e um sketch (setup/loop) com template proprio; no Moodle usa o
    # tipo base cpp_program (compila e compara stdout), mas com o template Arduino.
    coderunnertype = "cpp_program" if str(q.get("type", "")).lower() == "arduino" else str(q["type"])
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
    <coderunnertype>{escape(coderunnertype)}</coderunnertype>
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
    """True se p parece uma pasta de questao (question.json ou solucao, em p ou p/mdl)."""
    base = p.name
    for d in (p, p / "mdl"):
        if (d / "question.json").is_file():
            return True
        for n in (f"{base}_sol.cpp", "sol.cpp", f"{base}_sol.c", "sol.c",
                  f"{base}_sol.py", "sol.py"):
            if (d / n).is_file():
                return True
    return False


def expandir_pastas(paths):
    """Cada arg: uma pasta-questao vira ela mesma; uma pasta-contêiner vira suas
    subpastas-questao (ordenadas). Permite `questions` ou `questions/*`."""
    out = []
    for f in paths:
        p = Path(f)
        if p.name == "mdl" and p.parent != p:   # aceita .../questao/mdl -> .../questao
            p = p.parent
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

    # so precisa de Jobe se houver questao coderunner C/C++ (cloze e sql tratados a parte)
    if any(not q.get("_cloze") and not q.get("_sql") for q in questoes):
        ok, detalhe = jt.jobe_no_ar(jobe_url, apikey)
        if not ok:
            print(f"ERRO: Jobe indisponivel em {jobe_url}: {detalhe}\n"
                  "  docker run -d --name jobe -p 4000:80 trampgeek/jobeinabox:latest", file=sys.stderr)
            return False, []

    relatorio, tudo_ok = [], True
    for q in questoes:
        if q.get("_sql"):
            relatorio.append(f"  [--] {q['base']} (sql: expected gerado pelo gen_tests)")
            continue
        if q.get("_cloze"):
            relatorio.append(f"  [--] {q['base']} (cloze: sem execucao a validar)")
            continue
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


def _default_output(pastas):
    """Caminho padrao do -o quando omitido:
       1 questao  -> <pasta>/mdl/quiz_to_import.xml (dentro do mdl/ se existir)
       varias     -> <dir-pai-comum>/quiz_to_import.xml"""
    if len(pastas) == 1:
        return _mdl(pastas[0]) / "quiz_to_import.xml"
    pai = Path(os.path.commonpath([str(p) for p in pastas]))
    return pai / "quiz_to_import.xml"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gera XML CodeRunner (Moodle) de pasta(s) de questao.")
    ap.add_argument("folders", nargs="+",
                    help="pasta(s) de questao ou contêiner (ex.: questions/sqr, ou questions, ou questions/*)")
    ap.add_argument("-o", "--output",
                    help="arquivo .xml de saida (default: <pasta>/mdl/quiz_to_import.xml; use '-' p/ stdout)")
    ap.add_argument("--validate", dest="validate", action="store_true", default=True,
                    help="roda a referencia no Jobe antes de gerar; falha se algum teste nao passar (PADRAO)")
    ap.add_argument("--no-validate", dest="validate", action="store_false",
                    help="nao valida no Jobe antes de gerar")
    ap.add_argument("--jobe", default=DEFAULT_JOBE, help=f"URL do Jobe (default: {DEFAULT_JOBE}; ou env JOBE_URL)")
    ap.add_argument("--apikey", help="X-API-KEY do Jobe (para --validate)")
    args = ap.parse_args(argv)

    pastas = expandir_pastas(args.folders)
    if not pastas:
        ap.error("nenhuma pasta de questao valida encontrada")
    questoes = [carrega_questao(p, args.jobe, args.apikey) for p in pastas]

    if args.validate:
        tudo_ok, relatorio = validar(questoes, args.jobe, args.apikey)
        print("Validacao no Jobe:", file=sys.stderr)
        for linha in relatorio:
            print(linha, file=sys.stderr)
        if not tudo_ok:
            print("\nXML NAO gerado: corrija as questoes acima.", file=sys.stderr)
            return 1

    xml = render_quiz(questoes)
    if args.output == "-":
        sys.stdout.write(xml)
        return 0
    destino = Path(args.output) if args.output else _default_output(pastas)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(xml, encoding="utf-8")
    print(f"gravado: {destino}  ({len(questoes)} questao(oes))", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
