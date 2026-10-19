#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_xml_html.py — gera uma pagina HTML (Bootstrap) para VISUALIZAR um banco de
questoes Moodle XML (CodeRunner / Cloze / SQL) sem precisar importar no Moodle.

Lê o XML produzido pelo gen_moodle_xml.py (ou exportado do proprio Moodle) e monta
uma pagina com um cartao por questao: enunciado, resposta de referencia, mocks/schema
(globalextra), template, e a tabela de casos de teste. No fim da pagina, uma tabela
com as **configuracoes em comum** a todas as questoes (e uma nota do que varia).

Uso:
  python gen_xml_html.py banco.xml                 # grava banco.html
  python gen_xml_html.py banco.xml -o preview.html
  python gen_xml_html.py banco.xml --abrir         # tenta abrir no navegador

Sem dependencias externas (so a stdlib). O Bootstrap vem de CDN (pagina de preview
local, nao e um artefato do Moodle).
"""
import argparse
import html
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

BOOTSTRAP_CSS = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/css/bootstrap.min.css"
BOOTSTRAP_JS = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.8/dist/js/bootstrap.bundle.min.js"

# Campos de configuracao (escalares) considerados na tabela "em comum".
CONFIG_KEYS_CR = [
    "coderunnertype", "defaultgrade", "penalty", "allornothing", "penaltyregime",
    "precheck", "hidecheck", "showsource", "answerboxlines", "answerboxcolumns",
    "validateonsave", "displayfeedback",
]
CONFIG_KEYS_CLOZE = ["penalty", "hidden"]

ROTULO = {
    "coderunnertype": "Tipo CodeRunner", "defaultgrade": "Nota (pontos)",
    "penalty": "Penalidade", "allornothing": "Tudo ou nada", "penaltyregime": "Regime de penalidade",
    "precheck": "Precheck", "hidecheck": "Ocultar 'Check'", "showsource": "Mostrar fonte",
    "answerboxlines": "Linhas da caixa", "answerboxcolumns": "Colunas da caixa",
    "validateonsave": "Validar ao salvar", "displayfeedback": "Mostrar feedback",
    "hidden": "Oculta", "type": "Tipo (Moodle)",
}


def _txt(node):
    """Texto de um elemento (ou do filho <text>), tratando None -> ''."""
    if node is None:
        return ""
    t = node.find("text")
    if t is not None:
        return t.text or ""
    return node.text or ""


def _get(q, tag):
    return _txt(q.find(tag)) if q.find(tag) is not None else ""


# ---------------------------------------------------------------- Cloze -> HTML
_CLOZE_RE = re.compile(r"\{(\d*):(\w+):(.*?)\}", re.S)


def _cloze_campo_badge(m):
    peso, tipo, corpo = m.group(1), m.group(2), m.group(3)
    # opcoes separadas por ~; corretas comecam com = (ou %NN%); feedback apos #
    corretas = []
    for op in corpo.split("~"):
        op = op.split("#", 1)[0]          # tira feedback
        op = op.strip()
        if op.startswith("="):
            corretas.append(op[1:].strip())
        elif op.startswith("%") and "%" in op[1:]:
            # %NN%texto -> credito parcial; mostra tambem
            corretas.append(op.split("%", 2)[-1].strip() + " (parcial)")
    resp = " / ".join(c for c in corretas if c) or "?"
    tipo_curto = {
        "SHORTANSWER": "resposta curta", "SHORTANSWER_C": "resposta curta (maiusc.)",
        "NUMERICAL": "numerica", "MULTICHOICE": "multipla escolha",
        "MULTICHOICE_V": "multipla escolha", "MULTICHOICE_H": "multipla escolha",
        "MULTIRESPONSE": "multipla resposta",
    }.get(tipo, tipo)
    return (f'<span class="badge text-bg-warning text-dark me-1 mb-1" '
            f'title="{html.escape(m.group(0))}">▢ {tipo_curto}: '
            f'<strong>{html.escape(resp)}</strong></span>')


def cloze_para_html(texto):
    """Substitui os campos Cloze {..} por badges legiveis (resposta correta em destaque)."""
    return _CLOZE_RE.sub(_cloze_campo_badge, texto)


# ---------------------------------------------------------------- parse
def parse_questoes(xml_path):
    tree = ET.parse(xml_path)
    root = tree.getroot()
    questoes = []
    for q in root.findall("question"):
        tipo = q.get("type", "")
        if tipo in ("category", ""):   # pula categorias
            continue
        item = {"tipo": tipo, "name": _get(q, "name") or "(sem nome)",
                "questiontext": _get(q, "questiontext"),
                "generalfeedback": _get(q, "generalfeedback")}
        cfg = {"type": tipo}
        if tipo == "coderunner":
            for k in CONFIG_KEYS_CR:
                v = _get(q, k)
                if v != "":
                    cfg[k] = v
            item["answer"] = _get(q, "answer")
            item["answerpreload"] = _get(q, "answerpreload")
            item["globalextra"] = _get(q, "globalextra")
            item["template"] = _get(q, "template")
            item["testcases"] = []
            tcs = q.find("testcases")
            if tcs is not None:
                for tc in tcs.findall("testcase"):
                    item["testcases"].append({
                        "testcode": _txt(tc.find("testcode")),
                        "stdin": _txt(tc.find("stdin")),
                        "expected": _txt(tc.find("expected")),
                        "display": (_txt(tc.find("display")) or "SHOW").strip() or "SHOW",
                        "example": tc.get("useasexample", "0") == "1",
                        "mark": tc.get("mark", ""),
                    })
        elif tipo == "cloze":
            for k in CONFIG_KEYS_CLOZE:
                v = _get(q, k)
                if v != "":
                    cfg[k] = v
        item["cfg"] = cfg
        questoes.append(item)
    return questoes


# ---------------------------------------------------------------- render HTML
def _code_block(titulo, conteudo, lang="", collapse_id=None, aberto=False):
    if not conteudo.strip():
        return ""
    corpo = (f'<pre class="mb-0 p-3 bg-dark text-light rounded small" style="overflow:auto">'
             f'<code>{html.escape(conteudo)}</code></pre>')
    if collapse_id:
        show = "show" if aberto else ""
        return f'''
      <div class="mt-2">
        <button class="btn btn-sm btn-outline-secondary" data-bs-toggle="collapse"
                data-bs-target="#{collapse_id}">{html.escape(titulo)}</button>
        <div class="collapse {show} mt-2" id="{collapse_id}">{corpo}</div>
      </div>'''
    return f'<div class="mt-2"><div class="fw-semibold small text-muted">{html.escape(titulo)}</div>{corpo}</div>'


def _tabela_casos(casos, qid):
    if not casos:
        return ""
    linhas = []
    for i, c in enumerate(casos, 1):
        badges = ""
        if c["example"]:
            badges += '<span class="badge text-bg-success">exemplo</span> '
        if c["display"].upper() == "HIDE":
            badges += '<span class="badge text-bg-secondary">oculto</span> '
        tc = html.escape(c["testcode"]) or '<span class="text-muted">(vazio)</span>'
        stdin = html.escape(c["stdin"])
        exp = html.escape(c["expected"])
        linhas.append(
            f'<tr><td class="text-muted">{i}</td>'
            f'<td><code>{tc}</code></td>'
            f'<td><code>{stdin}</code></td>'
            f'<td><pre class="mb-0 small">{exp}</pre></td>'
            f'<td>{badges}</td></tr>')
    return f'''
      <div class="mt-2">
        <div class="fw-semibold small text-muted">Casos de teste ({len(casos)})</div>
        <div class="table-responsive">
        <table class="table table-sm table-bordered align-middle mb-0">
          <thead class="table-light"><tr>
            <th>#</th><th>Testcode</th><th>stdin</th><th>Esperado</th><th></th>
          </tr></thead>
          <tbody>{''.join(linhas)}</tbody>
        </table></div>
      </div>'''


def render_card(idx, q):
    tipo = q["tipo"]
    cfg = q["cfg"]
    # badges do cabecalho
    if tipo == "cloze":
        tipo_badge = '<span class="badge text-bg-info">Cloze</span>'
    else:
        crt = cfg.get("coderunnertype", "coderunner")
        cor = "text-bg-primary" if crt != "sql" else "text-bg-dark"
        tipo_badge = f'<span class="badge {cor}">CodeRunner · {html.escape(crt)}</span>'
    grade = cfg.get("defaultgrade")
    grade_badge = f'<span class="badge text-bg-light text-dark border">{html.escape(grade)} pt</span>' if grade else ""

    # enunciado (Cloze: transforma os campos {..} em badges legiveis)
    enun = q["questiontext"]
    if tipo == "cloze":
        enun = cloze_para_html(enun)

    partes = [f'<div class="qtext border rounded p-3 bg-body-tertiary">{enun}</div>']
    if tipo == "coderunner":
        partes.append(_code_block("Resposta de referência", q["answer"],
                                  collapse_id=f"ans{idx}", aberto=True))
        partes.append(_code_block("Base do aluno (answerpreload)", q.get("answerpreload", ""),
                                  collapse_id=f"pre{idx}"))
        partes.append(_code_block("Setup / mocks / schema (globalextra)", q.get("globalextra", ""),
                                  collapse_id=f"ge{idx}"))
        partes.append(_code_block("Template", q.get("template", ""), collapse_id=f"tpl{idx}"))
        partes.append(_tabela_casos(q.get("testcases", []), idx))
    if q.get("generalfeedback", "").strip():
        partes.append(f'<div class="mt-2 small"><span class="fw-semibold text-muted">'
                      f'Feedback geral:</span> {q["generalfeedback"]}</div>')

    return f'''
  <div class="card shadow-sm mb-4 questao" data-tipo="{html.escape(tipo)}"
       data-crt="{html.escape(cfg.get("coderunnertype",""))}">
    <div class="card-header d-flex flex-wrap gap-2 align-items-center">
      <span class="badge text-bg-secondary">#{idx}</span>
      <span class="fw-semibold flex-grow-1">{html.escape(q["name"])}</span>
      {grade_badge} {tipo_badge}
    </div>
    <div class="card-body">{''.join(p for p in partes if p)}</div>
  </div>'''


def tabela_comuns(questoes):
    """Configuracoes presentes em TODAS as questoes com o MESMO valor + o que varia."""
    if not questoes:
        return "", ""
    # chaves presentes em todas
    chaves = set(questoes[0]["cfg"].keys())
    for q in questoes[1:]:
        chaves &= set(q["cfg"].keys())
    comuns, variam = [], []
    for k in sorted(chaves):
        valores = {q["cfg"][k] for q in questoes}
        if len(valores) == 1:
            comuns.append((k, next(iter(valores))))
        else:
            variam.append((k, sorted(valores)))

    rot = lambda k: ROTULO.get(k, k)
    linhas_c = "".join(
        f'<tr><td class="fw-semibold">{html.escape(rot(k))}</td>'
        f'<td><code>{k}</code></td><td>{html.escape(str(v))}</td></tr>'
        for k, v in comuns)
    tab_comuns = f'''
    <table class="table table-sm table-striped table-bordered">
      <thead class="table-dark"><tr><th>Configuração</th><th>campo XML</th><th>Valor (comum a todas)</th></tr></thead>
      <tbody>{linhas_c or '<tr><td colspan="3" class="text-muted">nenhuma configuração é idêntica em todas as questões</td></tr>'}</tbody>
    </table>'''

    tab_variam = ""
    if variam:
        linhas_v = "".join(
            f'<tr><td class="fw-semibold">{html.escape(rot(k))}</td><td><code>{k}</code></td>'
            f'<td>{" · ".join(html.escape(str(x)) for x in vs)}</td></tr>'
            for k, vs in variam)
        tab_variam = f'''
    <p class="text-muted small mt-3 mb-1">Configurações que <strong>variam</strong> entre as questões:</p>
    <table class="table table-sm table-bordered">
      <thead class="table-light"><tr><th>Configuração</th><th>campo XML</th><th>Valores encontrados</th></tr></thead>
      <tbody>{linhas_v}</tbody>
    </table>'''
    return tab_comuns, tab_variam


def gerar_html(questoes, titulo):
    cards = "\n".join(render_card(i, q) for i, q in enumerate(questoes, 1))
    tab_comuns, tab_variam = tabela_comuns(questoes)
    n_cr = sum(1 for q in questoes if q["tipo"] == "coderunner")
    n_cz = sum(1 for q in questoes if q["tipo"] == "cloze")
    n_sql = sum(1 for q in questoes if q["cfg"].get("coderunnertype") == "sql")
    resumo = (f'{len(questoes)} questões · {n_cr} CodeRunner'
              + (f' (sendo {n_sql} SQL)' if n_sql else '') + f' · {n_cz} Cloze')

    return f'''<!doctype html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Preview — {html.escape(titulo)}</title>
<link href="{BOOTSTRAP_CSS}" rel="stylesheet">
<style>
  body {{ scroll-behavior: smooth; }}
  .qtext {{ overflow-x: auto; }}
  .qtext pre {{ white-space: pre-wrap; }}
  .card-header {{ background: #f8f9fa; }}
  pre code {{ white-space: pre; }}
  .sticky-top-bar {{ position: sticky; top: 0; z-index: 10; }}
</style>
</head>
<body class="bg-light">
<nav class="navbar navbar-dark bg-dark sticky-top-bar">
  <div class="container-xl">
    <span class="navbar-brand mb-0 h1">📋 Preview de questões</span>
    <span class="navbar-text text-light small">{html.escape(titulo)}</span>
  </div>
</nav>

<div class="container-xl my-4">
  <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
    <h5 class="mb-0 me-2">{resumo}</h5>
    <div class="btn-group btn-group-sm ms-auto" role="group" aria-label="filtro">
      <button class="btn btn-outline-dark active" data-filtro="todas">Todas</button>
      <button class="btn btn-outline-primary" data-filtro="coderunner">CodeRunner</button>
      <button class="btn btn-outline-dark" data-filtro="sql">SQL</button>
      <button class="btn btn-outline-info" data-filtro="cloze">Cloze</button>
    </div>
  </div>

  {cards}

  <h4 class="mt-5 mb-3" id="config">⚙️ Configurações em comum</h4>
  <p class="text-muted small">Campos presentes em todas as questões com o mesmo valor
  (não precisam ser ajustados questão a questão na importação).</p>
  {tab_comuns}
  {tab_variam}

  <footer class="text-muted small mt-5 pt-3 border-top">
    Gerado por <code>gen_xml_html.py</code> — pré-visualização; a correção real acontece no Moodle/Jobe.
  </footer>
</div>

<script src="{BOOTSTRAP_JS}"></script>
<script>
  // filtro por tipo
  document.querySelectorAll('[data-filtro]').forEach(btn => {{
    btn.addEventListener('click', () => {{
      document.querySelectorAll('[data-filtro]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const f = btn.dataset.filtro;
      document.querySelectorAll('.questao').forEach(c => {{
        let mostra = f === 'todas'
          || (f === 'sql' && c.dataset.crt === 'sql')
          || (f === c.dataset.tipo && f !== 'sql');
        c.style.display = mostra ? '' : 'none';
      }});
    }});
  }});
</script>
</body>
</html>
'''


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gera uma pagina HTML (Bootstrap) para visualizar um banco Moodle XML.")
    ap.add_argument("xml", help="arquivo .xml de questoes (Moodle XML)")
    ap.add_argument("-o", "--output", help="arquivo .html de saida (default: mesmo nome, .html)")
    ap.add_argument("--abrir", action="store_true", help="abrir no navegador padrao ao terminar")
    args = ap.parse_args(argv)

    xml_path = Path(args.xml)
    if not xml_path.is_file():
        print(f"ERRO: arquivo nao encontrado: {xml_path}", file=sys.stderr)
        return 2
    try:
        questoes = parse_questoes(xml_path)
    except ET.ParseError as e:
        print(f"ERRO: XML invalido: {e}", file=sys.stderr)
        return 2
    if not questoes:
        print("aviso: nenhuma questao (coderunner/cloze) encontrada no XML.", file=sys.stderr)

    out = Path(args.output) if args.output else xml_path.with_suffix(".html")
    out.write_text(gerar_html(questoes, xml_path.name), encoding="utf-8")
    print(f"gravado: {out}  ({len(questoes)} questao(oes))", file=sys.stderr)
    if args.abrir:
        import webbrowser
        webbrowser.open(out.resolve().as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
