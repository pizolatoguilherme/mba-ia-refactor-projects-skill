# Validation Guide (Phase 3)

Validation compares the refactored app against a **baseline captured from the original app**,
using the same requests in the same order from a fresh state. Work files live outside the project:
`WORK=${TMPDIR:-/tmp}/refactor-arch-<project-folder>` (create it with `mkdir -p`).

## §1 Runtime preparation

| Stack | Reuse if present | Otherwise |
|---|---|---|
| Python | `.venv/bin/python` (or `venv/`) | `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` |
| Node | `node_modules/` | `npm install` (use `npm ci` if a lock file exists) |
| Other | project wrapper (`./mvnw`, `go run`) | install per manifest |

Use the venv interpreter explicitly (`.venv/bin/python app.py`), not the system `python`.
Make sure the port is free before booting (`ss -ltn | grep :<port>` or `lsof -i :<port>`).

## §2 Endpoint inventory

From Phase 1, list every route as `METHOD PATH` with real parameter values. Use seed data to pick
IDs that exist. Include, for each resource: list, get existing, get missing (404), create valid,
create invalid (400), update, delete — whatever the original API supports. Use payload examples
from `api.http`/README when present.

**Order matters** — the script must be deterministic from a fresh database:
1. Read-only requests (GET) on seed data.
2. Creates (POST) → capture new IDs only if the API returns them deterministically; otherwise use
   known sequential IDs from a fresh DB.
3. Updates (PUT/PATCH) on created or seed records.
4. Deletes on records created by the script.
5. Destructive/admin endpoints last (e.g. reset database).

## §3 Smoke script

Write `$WORK/smoke.sh` once and reuse it unchanged for both runs. Each request prints one line:
`METHOD PATH -> STATUS | <first 150 chars of body>`.

```bash
#!/usr/bin/env bash
# usage: smoke.sh <base_url> <output_file>
BASE="$1"; OUT="$2"; : > "$OUT"
req() {  # req METHOD PATH [JSON_BODY] [EXTRA_HEADER]
  local m="$1" p="$2" body="$3" hdr="$4"
  local args=(-s -o /tmp/_rb -w '%{http_code}' -X "$m")   # separate `local`: $m must already be set
  [ -n "$body" ] && args+=(-H 'Content-Type: application/json' -d "$body")
  [ -n "$hdr" ] && args+=(-H "$hdr")
  local code; code=$(curl "${args[@]}" "$BASE$p")
  printf '%s %s -> %s | %s\n' "$m" "$p" "$code" "$(head -c 150 /tmp/_rb | tr '\n' ' ')" >> "$OUT"
}
req GET /health
req GET /produtos
req GET /produtos/1
req GET /produtos/9999
req POST /produtos '{"nome":"Teste","preco":10,"estoque":5,"categoria":"geral"}'
req POST /produtos '{"nome":"X"}'
# ... every endpoint ...
```
Admin endpoints guarded after refactoring: call them **twice** in the after-run — without the
header (expect 403) and with `X-Admin-Token: $ADMIN_TOKEN` (expect the baseline status). In the
baseline run, the call with header behaves like the call without it.

## §4 Boot, run, stop (baseline and after)

```bash
# fresh state: remove runtime DB files created by previous runs (gitignored artifacts only)
rm -f <db files, e.g. loja.db tasks.db instance/*.db>
# pre-steps if any (e.g. .venv/bin/python seed.py)
ADMIN_TOKEN=smoke-token <run command> > "$WORK/<phase>-server.log" 2>&1 &
PID=$!
for i in $(seq 1 30); do curl -s -o /dev/null "http://127.0.0.1:<port>/" && break; sleep 0.5; done
bash "$WORK/smoke.sh" "http://127.0.0.1:<port>" "$WORK/<phase>.txt"
kill $PID; wait $PID 2>/dev/null
```
- `<phase>` is `baseline` or `after`.
- Kill **by PID**, never with `pkill -f <pattern>` (it can kill your own shell).
- For in-memory databases each boot is already fresh.
- If the original app cannot boot (pre-existing bug), record that in the baseline and still
  require the refactored app to boot.

## §5 Compare

```bash
diff <(sed 's/ | .*//' "$WORK/baseline.txt") <(sed 's/ | .*//' "$WORK/after.txt")
```
- Status codes must match line by line, except intentional contract changes (mvc-guidelines §4).
- Also inspect bodies: same envelope keys (`dados`, `sucesso`, `erro`, …), same field names,
  sensitive fields gone. Timestamps/IDs may differ.
- Check the server log of the after-run: no tracebacks/uncaught errors.

## §6 Remaining anti-pattern scan

Re-run the Phase 2 grep helpers on the refactored tree, for example:
```bash
grep -rnE "execute\(.*(\+|%|\.format\(|f\")" --include=*.py .        # SQL built from strings
grep -rnE "(SECRET|PASSWORD|PASS|KEY|TOKEN)[A-Z_]*\s*[:=]\s*['\"][^'\"]+['\"]" --include=*.{py,js} . | grep -v example
grep -rnE "utcnow\(|\.query\.get\(|new Buffer\(" --include=*.{py,js} .
grep -rnE "^\s*except:\s*$|print\(|console\.log\(" --include=*.{py,js} .
```
(Exclude `.venv`, `node_modules`, `.claude`.) Every hit is either fixed or justified in the summary.

**`.env.example` completeness** — every variable read by the config must be listed:
```bash
grep -rhoE "environ(\.get)?\(\s*['\"][A-Z0-9_]+|getenv\(\s*['\"][A-Z0-9_]+|process\.env\.[A-Z0-9_]+" \
  --include=*.py --include=*.js . --exclude-dir=.venv --exclude-dir=node_modules --exclude-dir=.claude \
  | grep -oE "[A-Z0-9_]+$" | sort -u > /tmp/_vars_used
grep -oE "^[A-Z0-9_]+" .env.example | sort -u > /tmp/_vars_doc
comm -23 /tmp/_vars_used /tmp/_vars_doc   # must print nothing
```
If config reads variables through a helper (e.g. `_bool("FLASK_DEBUG")`), include those names too.

## §7 Cleanup and report

- Stop every process you started; delete runtime DB files created by the runs and `$WORK` temp
  files that are not needed anymore (keep `baseline.txt`/`after.txt` until the summary is printed).
- Do not leave `__pycache__`, `*.db` or logs inside the project.
- Fill the Validation section of the Phase 3 block with real numbers (`17/17 endpoints`).
  A check you did not run is ✗, not ✓.
