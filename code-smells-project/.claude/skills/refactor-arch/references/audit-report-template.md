# Audit Report Template (Phase 2)

The full report is saved to `<git root>/reports/audit-<project-folder>.md`; the conversation
shows the condensed version described in `SKILL.md` (Phase 2, step 9).
Fixed headers stay in English; descriptions, impacts and recommendations are in Portuguese.

## Rules

- Findings sorted **CRITICAL → HIGH → MEDIUM → LOW**; within a severity, by impact.
- IDs `F01..Fnn` follow the sorted order.
- `File:` always holds exact `path:line` or `path:start-end`, relative to the project root.
  Multiple locations are comma-separated or listed one per line. Lines must match the current
  file content (verify with `grep -n` / `sed -n 'X,Yp'`).
- **Never** write a bare filename or vague text ("controllers.py", "múltiplas funções", "todas as
  rotas") as a location — not in `File:` and not in the Summary table. If a finding spans a whole
  file, use its full range (`app.py:1-88`).
- The Summary table `Location` column shows the main `path:lines`; when there are more locations
  append `(+N)` — e.g. `models.py:28 (+18)`.
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
