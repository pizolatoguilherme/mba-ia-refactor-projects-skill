# MVC Architecture Guidelines (Phase 3 target)

## 1. Layers and responsibilities

For HTTP APIs, the "View" is the HTTP-facing layer: the route table plus the presentation of
responses (serialization). The rules below are language-independent.

| Layer | Owns | Must NOT contain |
|---|---|---|
| **Config** (`config/`) | Settings read from environment variables with safe dev defaults; constants (statuses, roles, limits, rates) | Secrets as literals, logic |
| **Database** (`database.*`) | Connection lifecycle (per request / pool / ORM session), schema init, seed helpers, transaction helper | Business rules, HTTP |
| **Models** (`models/`) | Entities/ORM classes and data access (repository functions with parameterized queries), entity-level rules (`is_overdue`, `can_cancel`), serialization of an entity **without sensitive fields** | HTTP objects (`request`, `res`), status codes, routing |
| **Controllers** (`controllers/`) | Application flow per use case: read input from the request, validate it, call models/services, decide the status code, return the response through the view/serializer | SQL, connection handling, long business calculations that belong to a model/service |
| **Views / Routes** (`views/` or `routes/`) | URL → controller mapping (Blueprint/Router), HTTP verbs, URL prefixes; response presenters if needed | Business rules, SQL, validation logic |
| **Services** (`services/`, optional) | Domain rules spanning several models or with side effects: checkout/payment, notifications, reports | HTTP objects |
| **Middlewares** (`middlewares/`) | Centralized error handler, admin/auth guard, request logging | Domain logic |
| **Validators** (optional, `validators/` or inside controllers module) | Reusable input validation returning errors | Persistence |
| **Entry point / composition root** | Create app (factory), load config, init DB, register routes and middlewares, start server | Route handlers, SQL, rules |

Dependency direction: `routes → controllers → services → models → database/config`.
Lower layers never import upper layers. Controllers never import the DB driver.

## 2. Target layouts

Pick by maturity (Phase 1). File names follow the project's language (Portuguese domain names
stay Portuguese: `produto_model.py`, not `product_model.py`).

### 2.1 Python / Flask — monolith (restructure into `src/`)
```
<project>/
├── app.py                      # thin entry point: from src.app import create_app; keeps `python app.py`
├── requirements.txt
├── .env.example                # documents every env var (no real secrets)
└── src/
    ├── __init__.py
    ├── app.py                  # create_app(): composition root
    ├── config/
    │   ├── __init__.py
    │   └── settings.py         # os.environ.get(...) + constants
    ├── database.py             # get_db() per request (flask.g), close on teardown, init_db(), seed
    ├── models/                 # one module per domain: <dominio>_model.py
    ├── controllers/            # one module per domain: <dominio>_controller.py
    ├── views/                  # Blueprints: <dominio>_routes.py (or routes.py if small)
    ├── services/               # optional: notification_service.py, relatorio_service.py
    └── middlewares/
        ├── error_handler.py    # AppError hierarchy + register_error_handlers(app)
        └── auth.py             # require_admin decorator (ADMIN_TOKEN)
```

### 2.2 Python / Flask — partially layered (complete in place)
Keep the existing top-level packages and their names (`models/`, `routes/`, `services/`,
`utils/`); keep import paths other scripts depend on (e.g. `seed.py` doing `from app import app, db`).
Add what is missing:
```
<project>/
├── app.py                      # create_app() + module-level `app` for compatibility
├── config/settings.py          # NEW: env-based config + constants (move from utils/app.py)
├── database.py                 # keep
├── models/                     # keep; add entity rules, safe serialization
├── controllers/                # NEW: one per resource; logic moved out of routes
├── routes/                     # keep name (acts as the View layer); handlers become 1–3 lines
│   └── <resource>_routes.py    # split resources that lived in the wrong module
├── services/                   # keep; inject config instead of literals; use or remove
├── middlewares/error_handler.py# NEW
└── utils/                      # keep only helpers actually used
```

### 2.3 Node.js / Express
```
<project>/
├── package.json                # `npm start` unchanged (adjust main/start only if entry moves)
├── .env.example
└── src/
    ├── app.js                  # composition root: createApp() + listen when run directly
    ├── config/index.js         # process.env + constants
    ├── database/connection.js  # open DB, promisified run/get/all, transaction helper, schema+seed
    ├── models/                 # <entity>Model.js: data access only
    ├── services/               # checkoutService.js, reportService.js (rules + transactions)
    ├── controllers/            # <resource>Controller.js: (req, res, next) handlers
    ├── routes/                 # express.Router() per resource + index.js mounting them
    └── middlewares/
        ├── errorHandler.js     # (err, req, res, next) + asyncHandler wrapper
        └── adminAuth.js        # optional ADMIN_TOKEN guard
```

### 2.4 Other stacks
Apply the same layer table with the framework's conventions (Rails `app/{models,controllers,views}`,
Spring `controller/service/repository`, Go `internal/{handler,service,repository}`, Laravel
`app/Http/Controllers` + `app/Models`). Do not fight framework conventions.

## 3. Rules

1. **Config**: every secret and environment-dependent value comes from env vars. Dev defaults are
   allowed only for non-secret values (port, DB path). For secrets without env value, generate a
   random ephemeral value at boot (`secrets.token_hex(32)` / `crypto.randomBytes(32)`) and log a
   warning — never ship a literal. `DEBUG` defaults to `False`. Ship `.env.example`.
2. **Database**: no shared mutable connection across threads. Flask + sqlite3: one connection per
   request in `flask.g`, closed in `teardown_appcontext`. ORM: use the framework's session.
   Node: one module owning the connection, exposing promise-based helpers and `transaction(fn)`.
3. **Queries**: always parameterized. Multi-step writes inside a transaction.
4. **Models** return plain data (dicts / objects) and never expose password or hash fields.
5. **Controllers** are thin: parse → validate → call → respond. Target ≤ ~25 lines per handler.
6. **Errors**: raise typed errors (`NotFoundError`, `ValidationError`, `ConflictError`,
   `UnauthorizedError`) from controllers/services; a single handler converts them to responses.
   Unknown exceptions → 500 with a generic message, full trace only in logs.
7. **Logging**: use the standard logger (`logging.getLogger(__name__)`, a small logger module in
   Node) instead of print/console.log for application events.
8. **Composition root**: an app factory (`create_app()` / `createApp()`) builds the app; module
   import must not start servers. The entry point keeps the original run command.
9. **No new dependencies** unless no standard/framework-bundled option exists. Prefer
   `werkzeug.security` (bundled with Flask) and Node's `crypto` for password hashing.
10. **Delete replaced files**: after moving code, remove the old monolithic files instead of
    leaving duplicates. Keep backward-compatible shims only when something external imports them.

## 4. External contract policy

Preserve for every original endpoint: path, HTTP method, success status code, JSON envelope
(e.g. `{"dados": ..., "sucesso": true}`) and **error envelope** (`{"erro": ...}`, `{"error": ...}`
or plain text — the error handler must reproduce the project's original format), field names,
request payload names (even cryptic ones such as `usr`, `eml` — rename only internally), port and
run command.

Allowed (and required) intentional changes — list each one under "Contract Changes":
- Removing sensitive fields from responses (passwords, hashes, secret keys, DB paths).
- Protecting endpoints that execute arbitrary SQL/code or wipe data: keep the route, require an
  `X-Admin-Token` header matching `ADMIN_TOKEN` from config; if `ADMIN_TOKEN` is unset the route
  answers 403. Do not delete these routes.
- Rejecting privilege escalation (e.g. ignore/deny client-chosen `admin` role) when the original
  flow allowed it.
- Turning crashes into proper 4xx responses (e.g. missing body → 400 instead of 500).

Not in scope by default (recommend in the report instead): adding authentication to endpoints
that were public, pagination that changes response shape, renaming public routes or fields.

## 5. Strategy by maturity

| Maturity | Strategy |
|---|---|
| Monolítica | Create the full layout (2.1 / 2.3), split by domain, move every function to its layer, then delete the old files. |
| Camadas parciais | Keep the folder conventions, add config/controllers/middlewares, move rules out of routes, reuse/clean existing helpers and services, split misplaced resources, fix code-level smells. |
| Em camadas | Fix findings locally; restructure only where a layer is violated. |
