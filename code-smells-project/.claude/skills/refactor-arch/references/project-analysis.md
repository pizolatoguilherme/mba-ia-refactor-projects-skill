# Project Analysis Heuristics (Phase 1)

Goal: build an accurate map of the project *before* judging it. Everything printed in the
Phase 1 block must be backed by a file you read.

## 1. Inventory

List source files while excluding dependency, tooling and generated directories:

```bash
find . -type f \
  -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/venv/*' \
  -not -path '*/.git/*' -not -path '*/.claude/*' -not -path '*/__pycache__/*' \
  -not -path '*/dist/*' -not -path '*/build/*' \
  -not -name '*.lock' -not -name 'package-lock.json' -not -name '*.db' | sort
```

- **Source files** = files in the application language(s) (`.py`, `.js`, `.ts`, `.rb`, `.go`,
  `.java`, `.php`, `.cs`…). Report docs/manifests separately if useful, never in the count.
- Count lines with `wc -l` on the source files only. Report the exact number of files and an
  approximate line total (`~800`).

## 2. Language and runtime

| Signal | Language |
|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`, `*.py` | Python |
| `package.json` (+ `*.js`/`*.ts`, `tsconfig.json`) | Node.js (JavaScript/TypeScript) |
| `Gemfile`, `*.rb` | Ruby |
| `go.mod`, `*.go` | Go |
| `pom.xml`, `build.gradle`, `*.java` | Java/Kotlin |
| `composer.json`, `*.php` | PHP |
| `*.csproj`, `*.cs` | C# |

Version hints: `python_requires`/`.python-version`, `engines.node` in `package.json`,
`.nvmrc`, `go` directive in `go.mod`. If none, report the runtime available locally
(`python3 --version`, `node --version`) and say it was detected from the environment.

## 3. Web framework

Look first at the manifest (with version), then confirm with imports in the entry point.

| Manifest entry / import | Framework |
|---|---|
| `flask` / `from flask import Flask` | Flask (Blueprints, `@app.route`, `add_url_rule`) |
| `django` / `django.urls` | Django |
| `fastapi` / `FastAPI()` | FastAPI |
| `express` / `require('express')`, `express()` | Express |
| `@nestjs/core` | NestJS |
| `fastify`, `koa`, `hapi` | Fastify / Koa / Hapi |
| `rails`, `sinatra` | Rails / Sinatra |
| `github.com/gin-gonic/gin`, `labstack/echo`, `net/http` | Gin / Echo / stdlib |
| `spring-boot-starter-web` | Spring Boot |
| `laravel/framework` | Laravel |

Version: the pinned/declared version in the manifest (`flask==3.1.1` → `Flask 3.1.1`;
`"express": "^4.18.2"` → `Express 4.x (^4.18.2)`). If `node_modules`/`.venv` exist you may
confirm the installed version (`npm ls express`, `pip show flask`).

**Dependencies line**: list the libraries that matter for architecture or security
(ORM/driver, CORS, auth, validation, HTTP clients, env loaders). Skip the framework itself.

## 4. Database / storage

| Signal | Storage |
|---|---|
| `import sqlite3`, `sqlite3.connect(...)`, npm `sqlite3`/`better-sqlite3` | SQLite (file path or `:memory:`) |
| `flask_sqlalchemy`, `SQLAlchemy`, `SQLALCHEMY_DATABASE_URI` | SQLAlchemy ORM (+ dialect from URI) |
| `psycopg2`, `pg`, `postgres://` | PostgreSQL |
| `pymysql`, `mysql2`, `mysql://` | MySQL |
| `pymongo`, `mongoose`, `mongodb://` | MongoDB |
| `redis` | Redis |
| none of the above, data in dicts/arrays | in-memory |

**Tables**: collect from `CREATE TABLE` statements, ORM models (`__tablename__`, class names),
migrations or schema files. List them in creation order.

Also note: where the connection is created (module global? per request? class attribute?),
whether the schema/seed runs at import or boot time, and whether a seed script must be run.

## 5. Entry point, run command and port

- Python: file with `app.run(...)` / `if __name__ == "__main__"`, or `create_app()`; port from
  `app.run(port=...)` (Flask default 5000). Run command from README or `python <entry>.py`.
- Node: `scripts.start` / `main` in `package.json`; port from `app.listen(...)` or config.
- Other stacks: `main()` / framework conventions.
- Note required pre-steps (e.g. `python seed.py`, migrations, `.env` file).

## 6. Endpoint inventory

Grep all route registrations and count them — this list becomes the smoke-test baseline.

| Stack | Patterns |
|---|---|
| Flask | `@<bp>.route(`, `@app.route(`, `add_url_rule(`, `methods=[...]` (default GET) |
| FastAPI | `@app.get/post/put/delete(`, `APIRouter` |
| Express | `app.get/post/put/patch/delete(`, `router.<verb>(`, `app.use('<prefix>', router)` |
| Django | `path(`/`re_path(` in `urls.py` |

Resolve prefixes (`url_prefix`, `app.use('/api', router)`). Also read request collections such as
`api.http`, `*.postman_collection.json`, or README examples — they show valid payloads.

## 7. Architecture maturity

| Maturity | Signals |
|---|---|
| **Monolítica** | ≤ ~5 source files hold routing + SQL + business rules; a single class/module owns several domains; no layer folders, or folders named after layers that contain everything |
| **Camadas parciais** | Folders such as `models/`, `routes/`, `services/`, `utils/` exist, but responsibilities leak: business rules/validation inside route handlers, unused service/helper layers, config hardcoded in the entry point, no centralized error handling, no controllers |
| **Em camadas** | Routes only delegate; controllers orchestrate; models/repositories own data access; config from environment; centralized error handling. Audit still runs — focus on code-level smells |

**File names are not layers.** A project whose layers are *single files* (`models.py`,
`controllers.py`, `utils.js`) each holding every domain, with SQL/rules/HTTP mixed, is
**Monolítica** — even though the file names look like MVC. "Camadas parciais" requires layer
*packages/folders* split by resource (e.g. `models/task.py`, `routes/user_routes.py`).

Write a one-line justification citing the concrete evidence (e.g.
"Monolítica — `AppManager.js` concentra schema, seed, rotas e pagamento").

## 8. Domain

Infer from table/model names, route paths and seed data. One line in Portuguese naming the
business and its main entities, e.g. "API de E-commerce (produtos, usuários, pedidos, relatórios)".

## 9. Output checklist

Before printing the Phase 1 block, confirm you have: language, framework+version, relevant deps,
domain, maturity + justification, exact source file count, entry point + run command + port,
DB tables, endpoint count. Unknown values are written as `não detectado` — never invented.
