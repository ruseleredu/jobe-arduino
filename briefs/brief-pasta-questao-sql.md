# Brief — Pasta de questão SQL (aluno ESCREVE a consulta)

Cole este brief num prompt de IA e preencha o "Pedido". A IA deve devolver os
arquivos de UMA pasta de questão do tipo **`sql`** no padrão do toolkit `jobe-arduino`.
Use este caso quando o aluno deve **escrever uma consulta** (SELECT/JOIN/GROUP BY/
funções de janela…) que é **executada no sqlite3 do Jobe** e corrigida pela saída.

O **Jobe executa SQL** (linguagem `sqlite3`). A questão vira `coderunnertype = sql` no
Moodle (CodeRunner): o protótipo `sql` embutido concatena **schema + resposta do aluno**
e roda no sqlite3, comparando a saída com o `expected`.

## Layout `mdl/` (atual)
Os arquivos ficam em **`<base>/mdl/`**. `<base>` é o nome da pasta.

## Arquivos a gerar em `<base>/mdl/`
1. `question.json` — `{ "name": "...", "type": "sql", ... }` (schema abaixo).
2. `questiontext.html` — enunciado (descreva a tabela e o que a consulta deve devolver).
3. `schema.sql` — **CREATE TABLE + INSERTs** que montam o banco de teste.
4. `<base>_sol.sql` — a **consulta de referência** CORRETA (o que o aluno deveria escrever).
5. (opcional) `answerpreload.sql` — esqueleto/comentário para o aluno começar.

NÃO gerar `*_tests.json` (o `gen_tests.py` gera rodando a referência contra o schema).

## `question.json`
```json
{
  "name": "Titulo visivel no Moodle",
  "type": "sql",
  "defaultgrade": 1,
  "allornothing": 1,
  "penaltyregime": "0, 10, 20, ..."
}
```

## Como monta e corrige
- O fonte executado = `schema.sql` + `\n` + consulta. A saída do sqlite3 é o `expected`.
- No XML: `schema.sql` vai em `<globalextra>`, a consulta de referência em `<answer>`,
  e o `tests.json` (um caso, `testcode` vazio) carrega o `expected`.

## ⚠️ Formato da saída (combine com o seu CodeRunner)
O `expected` é gerado no **formato list do sqlite3**: colunas separadas por `|`, **sem
cabeçalho**, uma linha por registro (o padrão do `sqlite3` CLI). O modo de saída do seu
protótipo `sql` no CodeRunner precisa ser o mesmo. Se for diferente (ex.: com
cabeçalho), **regenere** o `expected` no seu Jobe:
```bash
gen_tests.py quiz01/<base> --force
```

## Boas práticas
- **Dados determinísticos e pequenos** no `schema.sql` (poucas linhas, valores fixos),
  cobrindo o caso ensinado (ex.: um grupo com 3 linhas e outro com 2; uma linha `manual`).
- **Ordene** o resultado (`ORDER BY`) para a saída ser estável e comparável.
- Use `ROUND(...)` em médias para evitar ambiguidade de ponto flutuante.
- O enunciado deve deixar claras as colunas e a ordem esperadas.
- Evite `;` dentro de strings (o toolkit separa statements por `;`).

## Exemplo mínimo (ver `exemplos/sql/` — média por grupo)
`schema.sql`:
```sql
CREATE TABLE leituras (id INTEGER PRIMARY KEY, grupo TEXT, t REAL, origem TEXT);
INSERT INTO leituras (id, grupo, t, origem) VALUES
 (1,'a',24.5,'esp32'),(2,'a',31.2,'esp32'),(3,'b',22.0,'esp32'),(4,'a',-9.0,'manual');
```
`sql_sol.sql`:
```sql
SELECT grupo, ROUND(AVG(t),1) FROM leituras WHERE origem='esp32' GROUP BY grupo ORDER BY grupo;
```
`questiontext.html`:
```html
<p>Na tabela <code>leituras</code>, devolva <code>grupo</code> e a media de <code>t</code>
(1 casa) das leituras do ESP32, agrupando e ordenando por grupo.</p>
```
Saída esperada (gerada pelo `gen_tests.py`): `a|27.9` e `b|22.0`.

## Ideias de consulta (do fácil ao avançado)
`WHERE`/`ORDER BY` · `COUNT`/`AVG`/`MIN`/`MAX` com `GROUP BY` · `HAVING` ·
`JOIN` entre duas tabelas · funções de janela `LAG()`/`LEAD()` (diagnóstico de
sequência, duração de estados) · subconsultas.

## Comandos do autor (dentro do container de ferramentas)
```bash
gen_tests.py      quiz01/<base>     # roda a referência contra o schema -> <base>_tests.json
jobe_test.py      quiz01/<base>     # confere a referência (ou --answer consulta_do_aluno.sql)
gen_moodle_xml.py quiz01            # grava quiz01/quiz_to_import.xml (coderunnertype=sql)
```

## Pedido (preencher)
- **Base (nome da pasta):** …
- **Tabela(s) e dados** (`schema.sql`; ou descreva e peça à IA criar): …
- **O que a consulta deve devolver** (colunas, filtro, agrupamento, ordem): …
- **Nível** (filtro simples / agregação / HAVING / JOIN / função de janela): …
- **Consulta de referência** (ou peça à IA escrever): …

> Saída esperada da IA: apenas os arquivos da pasta `<base>/mdl/` (`question.json`,
> `questiontext.html`, `schema.sql`, `<base>_sol.sql`, e opcional `answerpreload.sql`),
> cada um em bloco de código rotulado com o caminho. Sem `tests.json`.
