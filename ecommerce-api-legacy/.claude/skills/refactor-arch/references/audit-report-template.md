# Audit Report Template (Phase 2)

The full report is saved to `<git root>/reports/audit-<project-folder>.md`; the conversation
shows the condensed version described in `SKILL.md` (Phase 2, step 9).
Fixed headers stay in English; descriptions, impacts and recommendations are in Portuguese.

## Rules

- Findings sorted **CRITICAL → HIGH → MEDIUM → LOW**; within a severity, by impact.
- IDs `F01..Fnn` follow the sorted order.
- `File:` always holds exact `path:line` or `path:start-end`, where `path` is the **full path
  relative to the project root, including every directory** (`src/utils.js:1-7`,
  `routes/task_routes.py:42` — never `utils.js:1-7` or `task_routes.py:42`). This applies to the
  Summary table, `File:`, the Deprecated APIs table and any location cited in the text.
  Multiple locations are comma-separated or listed one per line. Lines must match the current
  file content (verify with `grep -n` / `sed -n 'X,Yp'`).
- **Never** write a bare filename or vague text ("controllers.py", "múltiplas funções", "todas as
  rotas") as a location — not in `File:` and not in the Summary table. If a finding spans a whole
  file, use its full range (`app.py:1-88`).
- The Summary table `Location` column shows the main `path:lines`; when there are more locations
  append `(+N)` — e.g. `models.py:28 (+18)`.
- Comments inside `Evidence` code blocks that cite a location also use the full path
  (`// src/AppManager.js:68`, `# routes/user_routes.py:61`).
- Every `File:` line contains at least one `path:line` — never "ver tabela", "vários", etc. A
  finding that groups deprecated APIs lists its main locations in `File:` and the full list in the
  Deprecated APIs table.
- A range never ends past the last line of the file (`awk 'END{print NR}' <file>` gives the count).

## Mandatory self-check (run before printing the report)

Run from the project root, with `REPORT` pointing to the saved file. Every command must print
nothing; fix the report and re-run until they do.

```bash
REPORT=<path to the saved report>
# 1. every path:line(-line) cited exists and is within the file length
grep -oE '[A-Za-z0-9_./-]+\.(py|js|ts|jsx|tsx|rb|go|java|php|cs):[0-9]+(-[0-9]+)?' "$REPORT" | sort -u |
while IFS=: read -r f l; do
  if [ ! -f "$f" ]; then echo "MISSING PATH: $f (use the full path from the project root)"; continue; fi
  n=$(awk 'END{print NR}' "$f"); end=${l#*-}
  [ "$end" -le "$n" ] || echo "OUT OF RANGE: $f:$l (file has $n lines)"
done
# 2. every File: line has a line number
grep '^File:' "$REPORT" | grep -vE ':[0-9]+' 
# 3. summary counts and Total match the findings
for s in CRITICAL HIGH MEDIUM LOW; do
  c=$(grep -cE "^### F[0-9]+ \[$s\]" "$REPORT"); grep -qE "$s: $c( |$)" "$REPORT" || echo "COUNT MISMATCH: $s=$c"
done
t=$(grep -cE '^### F[0-9]+ ' "$REPORT"); grep -q "Total: $t findings" "$REPORT" || echo "TOTAL MISMATCH: $t"
```
- `Catalog:` holds the AP-ID(s) from `anti-patterns-catalog.md`; `Fix:` the playbook ID(s).
- `Evidence:` holds a short excerpt (1–3 lines) of the offending code.
- The summary counts must equal the number of findings listed.
- The Deprecated APIs section is always present (state "Nenhuma API deprecated encontrada" if empty).

## Template

````markdown
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <project folder name>
Stack:   <Language> + <Framework version>
Files:   <N> analyzed | ~<L> lines of code
Architecture: <maturity from Phase 1>
Date:    <YYYY-MM-DD>

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F01 | CRITICAL | <name> | <file:lines> |
| ... | ... | ... | ... |

## Findings

### F01 [CRITICAL] <Anti-pattern name>
File: <path:start-end>[, <path:line> ...]
Catalog: AP-xx | Fix: PB-xx
Evidence:
```<lang>
<1–3 lines of the offending code>
```
Description: <o que está errado, concretamente neste código>
Impact: <consequência real: segurança, manutenção, performance, testabilidade>
Recommendation: <transformação a aplicar, com o destino na arquitetura MVC>

### F02 [HIGH] <Anti-pattern name>
...

## Deprecated APIs
| File:line | Deprecated usage | Modern replacement |
|-----------|------------------|--------------------|
| <path:line> | <api> | <replacement> |

## Proposed Target Architecture
<árvore MVC proposta (resumida) e a estratégia: reestruturar monólito / completar camadas>

================================
Total: <N> findings
================================
````

After the closing block, print the confirmation prompt defined in `SKILL.md`
(`Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`) — it is part of the conversation
output, not of the saved file.

## Example finding (filled)

````markdown
### F02 [CRITICAL] SQL Injection
File: models.py:28, models.py:47-50, models.py:109-111
Catalog: AP-02 | Fix: PB-02
Evidence:
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
```
Description: Consultas SQL montadas por concatenação de strings com dados vindos do request,
incluindo a consulta de login.
Impact: Qualquer cliente pode ler/alterar o banco; `' OR '1'='1` faz bypass do login.
Recommendation: Usar queries parametrizadas (`?`) em todas as consultas, dentro dos models de cada domínio.
````
