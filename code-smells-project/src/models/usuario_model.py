from werkzeug.security import check_password_hash, generate_password_hash

from src.database import get_db

PUBLIC_COLUMNS = "id, nome, email, tipo, criado_em"


def _to_dict(row):
    return dict(row) if row else None


def find_all():
    rows = get_db().execute(f"SELECT {PUBLIC_COLUMNS} FROM usuarios").fetchall()
    return [_to_dict(r) for r in rows]


def find_by_id(usuario_id):
    row = get_db().execute(
        f"SELECT {PUBLIC_COLUMNS} FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()
    return _to_dict(row)


def create(nome, email, senha, tipo="cliente"):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        (nome, email, generate_password_hash(senha), tipo),
    )
    db.commit()
    return cursor.lastrowid


def count():
    return get_db().execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]


def authenticate(email, senha):
    row = get_db().execute(
        "SELECT id, nome, email, senha, tipo FROM usuarios WHERE email = ?", (email,)
    ).fetchone()
    if row and check_password_hash(row["senha"], senha):
        return {"id": row["id"], "nome": row["nome"], "email": row["email"], "tipo": row["tipo"]}
    return None
