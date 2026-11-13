# Refactoring Playbook (Phase 3)

Concrete transformations, each with **before → after** code. Python examples use Flask/sqlite3 or
Flask-SQLAlchemy; JS examples use Express/sqlite3. Translate the same move to other stacks.
Apply them in this order: PB-01 → PB-07 (foundation: config, DB, factory) → domain splits
(PB-05/06) → remaining fixes → PB-15 cleanup.

| ID | Transformation | Fixes |
|---|---|---|
| PB-01 | Externalize configuration and secrets | AP-01, AP-10 |
| PB-02 | Parameterized queries | AP-02 |
| PB-03 | Secure password hashing + safe serialization | AP-04, AP-05 |
| PB-04 | Guard dangerous/admin endpoints, stop privilege escalation | AP-03, AP-11 |
| PB-05 | Split God Module into model / controller / view per domain (Python) | AP-06, AP-19 |
| PB-06 | Split God Class into routes / controllers / services / models (Express) | AP-06 |
| PB-07 | App factory / composition root with injected dependencies | AP-09 |
| PB-08 | Move business rules out of controllers into models/services | AP-07, AP-14 |
| PB-09 | Remove N+1 and repeated aggregates | AP-13 |
| PB-10 | Callbacks → async/await with transactions | AP-12, AP-18 |
| PB-11 | Centralized error handling with typed errors | AP-16 |
| PB-12 | Replace global mutable state | AP-08 |
| PB-13 | Single reusable validation | AP-14, AP-15 |
| PB-14 | Replace deprecated APIs | AP-18 |
| PB-15 | Constants, naming, logging, dead code | AP-20…AP-24, AP-05 (logs) |
| PB-16 | Referential integrity on delete | AP-17 |

---

## PB-01 — Externalize configuration and secrets

**Before (Python)**
```python
app = Flask(__name__)
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
...
app.run(host="0.0.0.0", port=5000, debug=True)
```
**After**
```python
# src/config/settings.py
import os, secrets, logging

def _bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")

class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = _bool("FLASK_DEBUG", False)
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", "5000"))
    DB_PATH = os.environ.get("DB_PATH", "loja.db")
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")  # unset => admin routes disabled

if not os.environ.get("SECRET_KEY"):
    logging.getLogger(__name__).warning("SECRET_KEY not set; using an ephemeral random key")

# app.py (entry point)
from src.app import create_app
from src.config.settings import Settings

app = create_app()
if __name__ == "__main__":
    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
```
Keep the original host if clients depend on it (e.g. `0.0.0.0` in containers) — but read it from env.

**Before (JS)**
```js
const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_123", port: 3000 };
```
**After**
```js
// src/config/index.js
const crypto = require('crypto');
module.exports = Object.freeze({
  port: Number(process.env.PORT) || 3000,
  dbPath: process.env.DB_PATH || ':memory:',
  paymentGatewayKey: process.env.PAYMENT_GATEWAY_KEY || '',
  smtpUser: process.env.SMTP_USER || '',
  adminToken: process.env.ADMIN_TOKEN || null,
  sessionSecret: process.env.SESSION_SECRET || crypto.randomBytes(32).toString('hex'),
});
```
Add `.env.example` listing every variable with placeholder values.

---

## PB-02 — Parameterized queries

**Before (Python)**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
query += " AND (nome LIKE '%" + termo + "%' OR descricao LIKE '%" + termo + "%')"
```
**After**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))

clauses, params = ["1=1"], []
if termo:
    clauses.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]
if categoria:
    clauses.append("categoria = ?")
    params.append(categoria)
cursor.execute(f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params)  # only placeholders interpolated
```
**Before (JS)** `` db.get(`SELECT * FROM users WHERE id = ${req.params.id}`) ``
**After (JS)** `await db.get('SELECT * FROM users WHERE id = ?', [id])`

---

## PB-03 — Secure password hashing + safe serialization

**Before (Python)**
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()
def to_dict(self):
    return {"id": self.id, "email": self.email, "password": self.password}
```
**After**
```python
from werkzeug.security import generate_password_hash, check_password_hash  # bundled with Flask

def set_password(self, pwd):
    self.password = generate_password_hash(pwd)

def check_password(self, pwd):
    return check_password_hash(self.password, pwd)

def to_dict(self):
    return {"id": self.id, "email": self.email, "role": self.role}  # no password/hash
```
Plain sqlite login: fetch by email, then `check_password_hash(row["senha"], senha)`; seed data must
store hashes. Note in the summary that existing DB files with old hashes must be recreated.

**Before (JS)**
```js
function badCrypto(pwd) { let h = ""; for (let i = 0; i < 10000; i++) h += Buffer.from(pwd).toString('base64').substring(0, 2); return h.substring(0, 10); }
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
**After**
```js
// src/utils/password.js
const crypto = require('crypto');
const KEY_LENGTH = 64;
function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, KEY_LENGTH).toString('hex');
  return `${salt}:${hash}`;
}
function verifyPassword(password, stored) {
  const [salt, hash] = stored.split(':');
  const candidate = crypto.scryptSync(password, salt, KEY_LENGTH);
  return crypto.timingSafeEqual(candidate, Buffer.from(hash, 'hex'));
}
module.exports = { hashPassword, verifyPassword };

// logging: never the card or key
logger.info(`Processing payment for enrollment course=${courseId} card=****${card.slice(-4)}`);
```
Never assign a default password when the client omits one — reject with 400 or keep the original
contract's behavior documented.

---

## PB-04 — Guard dangerous/admin endpoints, stop privilege escalation

**Before**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    cursor.execute(request.get_json().get("sql"))
```
**After**
```python
# src/middlewares/auth.py
import hmac
from functools import wraps
from flask import request
from src.config.settings import Settings
from src.middlewares.error_handler import ForbiddenError

def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Admin-Token", "")
        if not Settings.ADMIN_TOKEN or not hmac.compare_digest(token, Settings.ADMIN_TOKEN):
            raise ForbiddenError("Acesso restrito a administradores")
        return fn(*args, **kwargs)
    return wrapper

# src/views/admin_routes.py
admin_bp.add_url_rule("/admin/query", view_func=require_admin(admin_controller.executar_query), methods=["POST"])
```
Inside the protected controller, still restrict what is allowed (e.g. read-only `SELECT` only)
when the endpoint executes SQL.

**JS**
```js
// src/middlewares/adminAuth.js
const crypto = require('crypto');
const { adminToken } = require('../config');
module.exports = (req, res, next) => {
  const sent = Buffer.from(req.get('X-Admin-Token') || '');
  const expected = Buffer.from(adminToken || '');
  if (!adminToken || sent.length !== expected.length || !crypto.timingSafeEqual(sent, expected)) {
    return res.status(403).json({ error: 'Forbidden' });
  }
  next();
};
```
**Privilege escalation**: `role = data.get('role', 'user')` accepted from public sign-up → validate
against allowed roles and only accept privileged roles when the caller is an authenticated admin;
otherwise force the default role (document as contract change).

---

## PB-05 — Split God Module per domain (Python)

**Before** — `models.py` (300+ lines) with products, users, orders, reports; `controllers.py`
with validation + notifications; `app.py` with routes + admin SQL.

**After**
```
src/models/produto_model.py       # data access for produtos only
src/models/usuario_model.py
src/models/pedido_model.py
src/controllers/produto_controller.py
src/controllers/pedido_controller.py
src/views/produto_routes.py       # Blueprint
src/services/notification_service.py
```
```python
# src/models/produto_model.py
from src.database import get_db

COLUMNS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"

def _to_dict(row):
    return dict(row) if row else None

def find_all():
    return [_to_dict(r) for r in get_db().execute(f"SELECT {COLUMNS} FROM produtos").fetchall()]

def find_by_id(produto_id):
    return _to_dict(get_db().execute(f"SELECT {COLUMNS} FROM produtos WHERE id = ?", (produto_id,)).fetchone())

def create(nome, descricao, preco, estoque, categoria):
    db = get_db()
    cur = db.execute(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        (nome, descricao, preco, estoque, categoria),
    )
    db.commit()
    return cur.lastrowid

# src/controllers/produto_controller.py
from flask import request, jsonify
from src.models import produto_model
from src.validators.produto_validator import validate_produto
from src.middlewares.error_handler import NotFoundError

def buscar_produto(id):
    produto = produto_model.find_by_id(id)
    if not produto:
        raise NotFoundError("Produto não encontrado")
    return jsonify({"dados": produto, "sucesso": True}), 200

def criar_produto():
    dados = validate_produto(request.get_json(silent=True))
    produto_id = produto_model.create(**dados)
    return jsonify({"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}), 201

# src/views/produto_routes.py
from flask import Blueprint
from src.controllers import produto_controller as c

produto_bp = Blueprint("produtos", __name__)
produto_bp.add_url_rule("/produtos", "listar_produtos", c.listar_produtos, methods=["GET"])
produto_bp.add_url_rule("/produtos/<int:id>", "buscar_produto", c.buscar_produto, methods=["GET"])
produto_bp.add_url_rule("/produtos", "criar_produto", c.criar_produto, methods=["POST"])
```
Partially layered projects: move a resource living in the wrong module (e.g. `/categories` inside
`report_routes.py`) to its own `category_routes.py` + `category_controller.py`.

---

## PB-06 — Split God Class (Express)

**Before**
```js
class AppManager {
  constructor() { this.db = new sqlite3.Database(':memory:'); }
  initDb() { /* CREATE TABLE + seed */ }
  setupRoutes(app) { app.post('/api/checkout', (req, res) => { /* 50 lines nested */ }); /* ... */ }
}
```
**After**
```js
// src/routes/index.js
const router = require('express').Router();
const asyncHandler = require('../middlewares/asyncHandler');
const checkout = require('../controllers/checkoutController');
const reports = require('../controllers/reportController');
const users = require('../controllers/userController');
router.post('/checkout', asyncHandler(checkout.create));
router.get('/admin/financial-report', asyncHandler(reports.financial));
router.delete('/users/:id', asyncHandler(users.remove));
module.exports = router;

// src/controllers/checkoutController.js
const checkoutService = require('../services/checkoutService');
exports.create = async (req, res) => {
  const { usr: name, eml: email, pwd: password, c_id: courseId, card } = req.body; // public names kept
  const result = await checkoutService.checkout({ name, email, password, courseId, card });
  res.status(200).json({ msg: 'Sucesso', enrollment_id: result.enrollmentId });
};

// src/models/courseModel.js
const db = require('../database/connection');
exports.findActiveById = (id) => db.get('SELECT * FROM courses WHERE id = ? AND active = 1', [id]);

// src/app.js (composition root)
const express = require('express');
const config = require('./config');
const db = require('./database/connection');
const routes = require('./routes');
const errorHandler = require('./middlewares/errorHandler');
function createApp() {
  const app = express();
  app.use(express.json());
  app.use('/api', routes);
  app.use(errorHandler);
  return app;
}
if (require.main === module) {
  db.init().then(() => createApp().listen(config.port, () => console.info(`LMS API on ${config.port}`)));
}
module.exports = { createApp };
```

---

## PB-07 — App factory / composition root

**Before**
```python
app = Flask(__name__)          # configured at import time
app.config[...] = ...
db.init_app(app)
app.register_blueprint(task_bp)
with app.app_context():
    db.create_all()            # side effect on import
```
**After**
```python
def create_app(settings=Settings):
    app = Flask(__name__)
    app.config.from_object(settings)
    CORS(app, origins=settings.CORS_ORIGINS)
    db.init_app(app)
    register_error_handlers(app)
    for bp in (task_bp, user_bp, category_bp, report_bp):
        app.register_blueprint(bp)
    with app.app_context():
        db.create_all()
    return app

app = create_app()   # kept only because external scripts import `app`
```
Services receive their dependencies (config, repositories) via constructor/function parameters
instead of instantiating concrete classes or reading literals internally.

---

## PB-08 — Move business rules out of controllers

**Before** (rule duplicated in 5 handlers)
```python
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            task_data['overdue'] = True
```
**After**
```python
# models/task.py
def is_overdue(self, now=None):
    now = now or utcnow()
    return bool(self.due_date and self.due_date < now and self.status not in CLOSED_STATUSES)

# controller / serializer
data = task.to_dict()
data["overdue"] = task.is_overdue()
```
**Before** (discount policy inside a data-access function)
```python
if faturamento > 10000: desconto = faturamento * 0.1
elif faturamento > 5000: desconto = faturamento * 0.05
```
**After**
```python
# src/config/settings.py
DISCOUNT_TIERS = ((10000, 0.10), (5000, 0.05), (1000, 0.02))

# src/services/relatorio_service.py
def calcular_desconto(faturamento):
    for limite, taxa in DISCOUNT_TIERS:
        if faturamento > limite:
            return faturamento * taxa
    return 0.0
```
Notifications printed inside controllers → `notification_service.pedido_criado(pedido)` called by
the controller/service.

---

## PB-09 — Remove N+1 and repeated aggregates

**Before (sqlite)**
```python
for row in pedidos:
    itens = db.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"])).fetchall()
    for item in itens:
        prod = db.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"])).fetchone()
```
**After**
```python
rows = db.execute("""
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario,
           COALESCE(pr.nome, 'Desconhecido') AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
    WHERE (? IS NULL OR p.usuario_id = ?)
    ORDER BY p.id
""", (usuario_id, usuario_id)).fetchall()
# group rows by pedido id in Python (one query total)
```
**Before (SQLAlchemy)** `for t in Task.query.all(): User.query.get(t.user_id)`
**After**
```python
from sqlalchemy.orm import joinedload
tasks = Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()
user_name = t.user.name if t.user else None
```
**Repeated counts → GROUP BY**
```python
counts = dict(db.session.query(Task.status, func.count(Task.id)).group_by(Task.status).all())
pending = counts.get("pending", 0)
```
**JS** — replace per-course/per-enrollment queries with one JOIN and aggregate in memory:
```js
const rows = await db.all(`
  SELECT c.id AS course_id, c.title, u.name AS student, p.amount, p.status
  FROM courses c
  LEFT JOIN enrollments e ON e.course_id = c.id
  LEFT JOIN users u ON u.id = e.user_id
  LEFT JOIN payments p ON p.enrollment_id = e.id
  ORDER BY c.id, e.id`);
```
Keep the original output order and shape.

---

## PB-10 — Callbacks → async/await with transactions

**Before**
```js
this.db.run("INSERT INTO enrollments ...", [userId, cid], function (err) {
  self.db.run("INSERT INTO payments ...", [this.lastID, price, status], function (err) {
    self.db.run("INSERT INTO audit_logs ...", [...], (err) => { res.json(...) });
  });
});
```
**After**
```js
// src/database/connection.js
const sqlite3 = require('sqlite3');
const config = require('../config');
const db = new sqlite3.Database(config.dbPath);
const run = (sql, params = []) => new Promise((resolve, reject) =>
  db.run(sql, params, function (err) { err ? reject(err) : resolve({ lastID: this.lastID, changes: this.changes }); }));
const get = (sql, params = []) => new Promise((resolve, reject) => db.get(sql, params, (e, r) => (e ? reject(e) : resolve(r))));
const all = (sql, params = []) => new Promise((resolve, reject) => db.all(sql, params, (e, r) => (e ? reject(e) : resolve(r))));
async function transaction(fn) {
  await run('BEGIN');
  try { const out = await fn(); await run('COMMIT'); return out; }
  catch (err) { await run('ROLLBACK'); throw err; }
}
module.exports = { run, get, all, transaction };

// src/services/checkoutService.js
return db.transaction(async () => {
  const { lastID: enrollmentId } = await enrollmentModel.create(userId, course.id);
  await paymentModel.create(enrollmentId, course.price, PAYMENT_STATUS.PAID);
  await auditLogModel.record(`Checkout curso ${course.id} por ${userId}`);
  return { enrollmentId };
});
```
Note: a single shared sqlite3 connection serializes statements, so concurrent requests can
interleave inside a transaction; for SQLite keep one transaction at a time (a simple promise
queue/mutex in `transaction`) or use a driver with explicit connections.
Python sqlite3: wrap multi-step writes in `with db:` (commits or rolls back).

---

## PB-11 — Centralized error handling

**Before**
```python
def buscar_produto(id):
    try:
        ...
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
```
**After**
```python
# src/middlewares/error_handler.py
import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException
log = logging.getLogger(__name__)

class AppError(Exception):
    status_code = 400
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message
        if status_code: self.status_code = status_code

class ValidationError(AppError): status_code = 400
class UnauthorizedError(AppError): status_code = 401
class ForbiddenError(AppError): status_code = 403
class NotFoundError(AppError): status_code = 404
class ConflictError(AppError): status_code = 409

def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"erro": err.message, "sucesso": False}), err.status_code   # project's envelope

    @app.errorhandler(HTTPException)
    def handle_http(err):
        return jsonify({"erro": err.description, "sucesso": False}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        log.exception("Unhandled error")
        return jsonify({"erro": "Erro interno do servidor", "sucesso": False}), 500
```
Use the **original envelope key** of the project (`erro`, `error`, plain text).

**Express**
```js
// src/middlewares/asyncHandler.js
module.exports = (fn) => (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next);

// src/middlewares/errorHandler.js
const { AppError } = require('../errors');
module.exports = (err, req, res, next) => {
  if (err instanceof AppError) return res.status(err.status).send(err.message); // original format: plain text
  console.error(err);
  res.status(500).send('Erro interno');
};
```

---

## PB-12 — Replace global mutable state

**Before**
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
    return db_connection
```
**After**
```python
# src/database.py
import sqlite3
from flask import g, current_app

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_schema(get_db())
        seed_if_empty(get_db())
```
**JS**: `let globalCache = {}; let totalRevenue = 0;` exported and mutated → remove if unused; if
needed, encapsulate in a module with explicit functions (`cache.set/get`) or compute values from the
DB (revenue = `SUM(amount)` query) instead of a mutable counter.

---

## PB-13 — Single reusable validation

**Before** — create and update handlers each repeat ~20 lines of `if "nome" not in dados ...`.
**After**
```python
# src/validators/produto_validator.py
from src.config.settings import CATEGORIAS_VALIDAS, NOME_MIN, NOME_MAX
from src.middlewares.error_handler import ValidationError

def validate_produto(dados):
    if not dados:
        raise ValidationError("Dados inválidos")
    for campo, label in (("nome", "Nome"), ("preco", "Preço"), ("estoque", "Estoque")):
        if campo not in dados:
            raise ValidationError(f"{label} é obrigatório")
    if not isinstance(dados["preco"], (int, float)) or dados["preco"] < 0:
        raise ValidationError("Preço não pode ser negativo")
    ...
    return {"nome": dados["nome"], "descricao": dados.get("descricao", ""), ...}
```
Keep the original error messages and status codes so clients see the same responses. Add type
checks where the original crashed with 500 (e.g. `priority` as string → 400).
Prefer `request.get_json(silent=True)` so an invalid/empty body becomes a 400, not a 500.

---

## PB-14 — Replace deprecated APIs

**Before**
```python
task = Task.query.get(task_id)
created_at = db.Column(db.DateTime, default=datetime.utcnow)
if t.due_date < datetime.utcnow(): ...
```
**After**
```python
task = db.session.get(Task, task_id)

# utils/time.py — one place for "now" (naive UTC keeps compatibility with existing SQLite rows)
from datetime import datetime, timezone
def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)

created_at = db.Column(db.DateTime, default=utcnow)
```
**JS**
```js
new Buffer(pwd)            →  Buffer.from(pwd)
url.parse(req.url)         →  new URL(req.url, `http://${req.headers.host}`)
res.send(404, 'x')         →  res.status(404).send('x')
var x = 1                  →  const x = 1
db.get(sql, p, cb) nesting →  await get(sql, p)   (PB-10)
```

---

## PB-15 — Constants, naming, logging, dead code

**Before**
```python
import os, sys, json, datetime     # only datetime used
print("Produto criado com ID: " + str(id))
if novo_status not in ["pendente", "aprovado", "enviado", "entregue", "cancelado"]: ...
if type(tags) == list: ...
def is_admin(self):
    if self.role == 'admin':
        return True
    else:
        return False
```
**After**
```python
import logging
from src.config.settings import STATUS_PEDIDO_VALIDOS
log = logging.getLogger(__name__)

log.info("Produto criado com ID %s", produto_id)
if novo_status not in STATUS_PEDIDO_VALIDOS: ...
if isinstance(tags, list): ...
def is_admin(self):
    return self.role == ROLE_ADMIN
```
**JS naming**
```js
let u = req.body.usr; let e = req.body.eml; let cc = req.body.card;
// →
const { usr: name, eml: email, card } = req.body;   // public field names unchanged
if (cc.startsWith("4"))  →  if (card.startsWith(APPROVED_CARD_PREFIX))
```
Configure logging once in the composition root (`logging.basicConfig(level=...)`).

---

## PB-16 — Referential integrity on delete

**Before**
```js
app.delete('/api/users/:id', (req, res) => {
  db.run("DELETE FROM users WHERE id = ?", [id], (err) => res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."));
});
```
**After**
```js
// src/services/userService.js
exports.remove = (userId) => db.transaction(async () => {
  const enrollments = await enrollmentModel.findByUser(userId);
  await paymentModel.deleteByEnrollmentIds(enrollments.map((e) => e.id));
  await enrollmentModel.deleteByUser(userId);
  const { changes } = await userModel.remove(userId);
  return changes > 0;
});
```
SQLAlchemy: declare `cascade="all, delete-orphan"` on the relationship or delete/reassign children
explicitly inside the same session commit. Keep the original success status/message unless it
leaked internal state — then document the new message as a contract change.
