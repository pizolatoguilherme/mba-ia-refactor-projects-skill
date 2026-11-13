# Anti-Patterns Catalog (Phase 2)

Each entry has: **ID**, **default severity**, **detection signals** (concrete things to grep/read
for, per stack), **why it matters**, and the **playbook** transformation that fixes it
(`refactoring-playbook.md`). Signals are written per language but the *idea* is universal —
for other stacks, look for the equivalent construct.

## Severity scale

| Severity | Definition |
|---|---|
| **CRITICAL** | Severe security or architecture failure: exposes sensitive data or allows attack (hardcoded credentials, SQL injection, unauthenticated arbitrary SQL), or completely violates separation of concerns (God Class with DB + rules + routing in one unit). |
| **HIGH** | Strong MVC/SOLID violation that makes maintenance and testing very hard: heavy business logic in controllers/routes, tight coupling without DI, global mutable state, insecure runtime defaults, broken auth. |
| **MEDIUM** | Standardization, duplication or moderate performance issues: N+1 queries, duplicated logic, missing validation, swallowed errors, deprecated APIs. |
| **LOW** | Readability: naming, magic numbers, unused imports, print-logging, non-idiomatic constructs. |

Rules: use the catalog severity as the floor; raise it only with a concrete justification.
Group repeated occurrences of the same anti-pattern into one finding with all locations.

## Index

| ID | Anti-pattern | Severity | Playbook |
|---|---|---|---|
| AP-01 | Hardcoded credentials / secrets | CRITICAL | PB-01 |
| AP-02 | SQL injection (query built from strings) | CRITICAL | PB-02 |
| AP-03 | Arbitrary SQL/code execution or destructive admin endpoint without auth | CRITICAL | PB-04 |
| AP-04 | Plaintext or weak password hashing | CRITICAL | PB-03 |
| AP-05 | Sensitive data exposure (responses / logs) | CRITICAL | PB-03, PB-15 |
| AP-06 | God Class / God Module | CRITICAL | PB-05, PB-06 |
| AP-07 | Business logic in controllers/routes (fat controller) | HIGH | PB-08 |
| AP-08 | Global mutable state / shared connection singleton | HIGH | PB-12 |
| AP-09 | Tight coupling, no dependency injection, import-time side effects | HIGH | PB-07 |
| AP-10 | Insecure runtime defaults (debug on, secrets in health/info) | HIGH | PB-01 |
| AP-11 | Broken authentication / authorization | HIGH | PB-04 |
| AP-12 | Callback hell / multi-step write without transaction | HIGH | PB-10 |
| AP-13 | N+1 queries and repeated aggregate queries | MEDIUM | PB-09 |
| AP-14 | Duplicated logic (validation, serialization, rules) | MEDIUM | PB-13, PB-08 |
| AP-15 | Missing / inconsistent input validation | MEDIUM | PB-13 |
| AP-16 | Swallowed exceptions, bare `except`, internal errors leaked to clients | MEDIUM | PB-11 |
| AP-17 | Missing referential integrity on delete | MEDIUM | PB-16 |
| AP-18 | Deprecated / legacy APIs | MEDIUM | PB-14 |
| AP-19 | Misplaced responsibility (resource in the wrong module, unused layer) | MEDIUM | PB-05 |
| AP-20 | Magic numbers / magic strings | LOW | PB-15 |
| AP-21 | Poor naming (cryptic identifiers) | LOW | PB-15 |
| AP-22 | Unused imports / dead code | LOW | PB-15 |
| AP-23 | `print` / `console.log` used as logging | LOW | PB-15 |
| AP-24 | Non-idiomatic constructs | LOW | PB-15 |

---

## CRITICAL

### AP-01 — Hardcoded credentials / secrets
**Signals**
- Python: `app.config["SECRET_KEY"] = "<literal>"`, `password = '...'`, `api_key = "..."`,
  `SQLALCHEMY_DATABASE_URI` with user:pass, SMTP user/password literals in classes.
- JS: object literals like `{ dbPass: "...", paymentGatewayKey: "pk_live_..." }`,
  `jwtSecret: '...'`, connection strings with credentials.
- Generic: identifiers matching `secret|password|passwd|pwd|token|api[_-]?key|private` assigned
  to a string literal; prefixes `pk_live_`, `sk_live_`, `AKIA`, `ghp_`.
**Why**: anyone with repo access (or a leaked image) gets production credentials; rotating
requires a code change.
**Not a finding**: placeholder values read from env with a clearly fake dev default *and* a
startup warning.

### AP-02 — SQL injection
**Signals**
- Python: `cursor.execute("... " + var)`, f-strings or `%`/`.format()` inside SQL,
  `query += " AND col = '" + value + "'"`, `text(f"...")` in SQLAlchemy.
- JS: template literals `` `SELECT ... ${id}` `` or `+` concatenation passed to
  `db.run/get/all/query`.
- Login queries comparing `email = '" + email + "'` → authentication bypass (`' OR '1'='1`).
**Why**: full read/write access to the DB by any client. Always CRITICAL.

### AP-03 — Arbitrary SQL/code execution or destructive admin endpoint without auth
**Signals**: a route that executes SQL/commands received in the request (`cursor.execute(dados["sql"])`,
`eval`, `exec`, `child_process.exec(req.body...)`); routes like `/admin/reset-db`,
`/admin/query`, `/debug/*` that delete/alter data with no authentication check.
**Why**: remote attacker can dump or destroy the database in one request.

### AP-04 — Plaintext or weak password hashing
**Signals**
- Passwords stored/compared as received: `INSERT ... senha` with raw value, `WHERE senha = ?`.
- Fast/broken hashes for passwords: `hashlib.md5`, `sha1`, unsalted `sha256`, base64,
  home-made loops (`for (i<10000) hash += Buffer.from(pwd).toString('base64')…`), truncation.
- Default passwords assigned when the client omits one (`p || "123456"`).
**Why**: a DB leak exposes every user's password (credential stuffing elsewhere).

### AP-05 — Sensitive data exposure (responses / logs)
**Signals**
- Serializers returning `password`/`senha`/hash fields (`to_dict()` including `password`,
  `SELECT *` rows returned as-is for users).
- Health/info endpoints returning `secret_key`, DB paths, debug flags.
- Logs printing card numbers, tokens, gateway keys, passwords (`console.log(\`card ${cc} key ${key}\`)`).
**Why**: credentials and PCI data leak to any client or to log aggregation.

### AP-06 — God Class / God Module
**Signals**
- One class/module owns several of: DB connection/schema, seed data, route registration,
  business rules, payment/notification side effects, reporting (e.g. `AppManager` with
  `initDb()` + `setupRoutes()` + checkout logic).
- One module holds data access for 3+ unrelated domains (products, users, orders…) together with
  business rules (discount calculation, stock control).
- File > ~300 lines mixing layers; functions > ~50 lines doing I/O + rules + formatting.
**Why**: impossible to test in isolation; every change risks every feature.
Severity: CRITICAL when it mixes data access + business rules + routing/HTTP; HIGH when it is a
single-layer module that is merely too large.

---

## HIGH

### AP-07 — Business logic in controllers/routes (fat controller)
**Signals**: route handlers that validate fields, compute totals/discounts/overdue status, build
complex aggregates, call several models and send notifications; the same rule written in several
handlers; controllers issuing SQL directly.
**Why**: rules cannot be reused or unit-tested without HTTP; violates SRP.

### AP-08 — Global mutable state / shared connection singleton
**Signals**: module-level `db_connection = None` + `global db_connection`;
`sqlite3.connect(..., check_same_thread=False)` shared across threads; exported mutable objects
(`let globalCache = {}`, `let totalRevenue = 0` exported by value); in-memory lists on singletons
used as storage (`self.notifications = []`).
**Why**: race conditions, hidden coupling, state that is lost/inconsistent between workers.

### AP-09 — Tight coupling, no dependency injection, import-time side effects
**Signals**: controllers/classes instantiating concrete dependencies internally
(`new sqlite3.Database(...)` inside a class constructor, `NotificationService()` created inside a
handler); app object created and configured at import time with no factory; `db.create_all()` or
seeds executed on import; circular imports between layers.
**Why**: no way to swap DB/services in tests; boot order bugs.

### AP-10 — Insecure runtime defaults
**Signals**: `debug=True` / `app.config["DEBUG"] = True` hardcoded (Werkzeug debugger = remote code
execution), `host="0.0.0.0"` with debug, `CORS(app)` allowing every origin with credentials,
health endpoint reporting `"ambiente": "producao"` while in debug.
**Why**: exposes interactive debugger and stack traces in production.

### AP-11 — Broken authentication / authorization
**Signals**: fake tokens (`'fake-jwt-token-' + id`), role chosen by the client on sign-up
(`role = data.get('role')` accepting `admin`), admin/financial/delete routes with no auth check,
login returning the user record including the password hash.
**Why**: privilege escalation and unauthenticated access to sensitive operations.
Note: implementing a full auth system is usually out of refactoring scope — recommend it; but fix
privilege escalation and protect destructive admin routes (PB-04).

### AP-12 — Callback hell / multi-step write without transaction
**Signals**: 3+ nested callbacks (`db.get(..., () => db.run(..., () => db.run(...)))`),
`const self = this` workarounds, manual pending counters (`coursesPending--`); several dependent
writes (order + items + stock, enrollment + payment + audit) without `BEGIN/COMMIT/ROLLBACK`.
**Why**: partial writes leave inconsistent data; errors are lost; flow is unreadable.

---

## MEDIUM

### AP-13 — N+1 queries and repeated aggregate queries
**Signals**
- A query inside a loop over rows of another query (`for row in pedidos: cursor.execute(... itens ...)`,
  `for t in tasks: User.query.get(t.user_id)`, `courses.forEach(c => db.all(...))`).
- ORM lazy relationships accessed in loops (`len(u.tasks)` for each user).
- Many `COUNT(*)` queries that differ only by a filter value (`filter_by(status='pending').count()`,
  `...status='done'...`) instead of one `GROUP BY`.
**Why**: query count grows with data volume; latency spikes.

### AP-14 — Duplicated logic
**Signals**: the same validation block in create and update handlers; the same `row → dict`
mapping repeated in several functions; the same business rule (e.g. "is overdue") recomputed in
several files while a model method already exists; two functions identical except for a WHERE clause.
**Why**: rules diverge silently over time.

### AP-15 — Missing / inconsistent input validation
**Signals**: `request.get_json()` used without checking for `None` (`dados.get(...)` → 500 on
empty body); numeric fields compared without type check (`priority < 1` with a string → TypeError);
update endpoints that skip validations the create endpoint has; IDs from the path passed unchecked.
**Why**: client errors become 500s; invalid data is persisted.

### AP-16 — Swallowed exceptions / leaked internals
**Signals**: bare `except:` or `except Exception: pass`; callbacks ignoring `err`
(`(err, rows) => { rows.length ... }`); every handler wrapped in `try/except Exception as e:
return {"erro": str(e)}, 500` (leaks internals, duplicates handling); no centralized error handler.
**Why**: bugs are hidden; stack details leak to clients; inconsistent error format.

### AP-17 — Missing referential integrity on delete
**Signals**: deleting a parent row without handling children (users → enrollments/payments,
categories → tasks); responses admitting dirty data; SQLite without `PRAGMA foreign_keys = ON`;
errors in the delete callback ignored.
**Why**: orphan rows corrupt reports and later inserts.

### AP-18 — Deprecated / legacy APIs
Detect usages of APIs that are deprecated or legacy **for the versions declared in the manifest
and the runtime in use**, and recommend the modern equivalent. Severity MEDIUM by default; HIGH if
the API is already removed in the installed version (will crash); LOW if purely stylistic.

| Stack | Deprecated / legacy usage | Modern replacement |
|---|---|---|
| Python ≥3.12 | `datetime.utcnow()`, `datetime.utcfromtimestamp()` | `datetime.now(timezone.utc)`, `datetime.fromtimestamp(ts, timezone.utc)` |
| SQLAlchemy 2.x / Flask-SQLAlchemy 3.x | `Model.query.get(id)` (legacy `Query.get`) | `db.session.get(Model, id)` / `db.get_or_404(Model, id)` |
| SQLAlchemy 2.x | `Model.query.filter(...)` legacy Query API (style) | `db.session.execute(db.select(Model).where(...)).scalars()` |
| Flask ≥2.3 | `@app.before_first_request`, `flask.json.JSONEncoder`, `app.json_encoder` | app factory init code, `app.json` provider |
| Python ≥3.12 | `distutils`, `imp`, `asynchat`, `asyncore` | `setuptools`/`packaging`, `importlib`, `asyncio` |
| Python sqlite3 ≥3.12 | default datetime adapters/converters | explicit adapters or ISO strings |
| Python | `pkg_resources` | `importlib.metadata` / `importlib.resources` |
| Node | `new Buffer(x)` / `Buffer(x)` | `Buffer.from(x)` / `Buffer.alloc(n)` |
| Node | `url.parse()`, `querystring` | `new URL()`, `URLSearchParams` |
| Node | `crypto.createCipher()` | `crypto.createCipheriv()` |
| Node | `fs.exists()`, `util.isArray()` etc. | `fs.existsSync()`/`fs.promises.access`, `Array.isArray()` |
| Node | callback-only DB/fs APIs with nested callbacks (`sqlite3` `db.run(sql, cb)`) | promise wrappers / `util.promisify` / `fs.promises` + `async/await` |
| Express 4→5 | `req.param()`, `res.send(status, body)`, `res.json(status, obj)`, `app.del()`, standalone `body-parser` | `req.params/query/body`, `res.status(s).send()`, `app.delete()`, `express.json()` |
| JS | `var` declarations | `const` / `let` |

Grep helpers: `grep -rn "utcnow\|\.query\.get(\|before_first_request" --include=*.py .`,
`grep -rn "new Buffer\|url.parse\|createCipher(\|req.param(" --include=*.js .`.
If nothing is found, write "Nenhuma API deprecated encontrada" in the report section.

### AP-19 — Misplaced responsibility / unused layer
**Signals**: a resource's CRUD living in another resource's module (categories inside
`report_routes`); helper/service/validator modules that exist but are never imported while the
same logic is re-implemented in handlers; constants declared and never used.
**Why**: misleading structure; the "organized" layer is fake.

---

## LOW

### AP-20 — Magic numbers / strings
**Signals**: thresholds and rates inline (`if faturamento > 10000: desconto = faturamento * 0.1`),
status/role/category lists hardcoded in handlers, `cc.startsWith("4")`, `len(password) < 4`,
`range(1, 5)` priorities, ports.

### AP-21 — Poor naming
**Signals**: single-letter or cryptic identifiers for domain values (`u, e, p, cid, cc`),
generic names (`data`, `result`, `d`) for domain objects, names that lie (`badCrypto`,
`logAndCache` that does two things), mixed languages inside the same layer without reason.

### AP-22 — Unused imports / dead code
**Signals**: imports never referenced (`import os, sys, json` unused), functions never called,
commented-out blocks, variables assigned and never read.
Check with `grep -n "^import\|^from" file` then search each name.

### AP-23 — print / console.log as logging
**Signals**: `print("ERRO: ...")`, `print(f"Task criada ...")`, `console.log('[LOG] ...')`
in application code.
**Why**: no levels, no structure, no way to silence or route logs.

### AP-24 — Non-idiomatic constructs
**Signals**: `type(x) == list` (use `isinstance`), `if cond: return True else: return False`
(return the expression), deeply nested `if` pyramids that could be guard clauses,
`let` for never-reassigned values, `== None`.

---

## Detection procedure (summary)

1. For each file, read it fully once; note candidates per AP-ID with exact lines.
2. Run the grep helpers for repeated signals (SQL concatenation, secrets, `print(`, `except:`,
   `utcnow`, `.query.get(`, nested callbacks).
3. Cross-check layers: is each helper/service actually imported? Does each model method get used
   or re-implemented elsewhere?
4. Build findings, cluster repeated locations, sort by severity, number them.
