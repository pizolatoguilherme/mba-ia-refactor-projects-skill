from werkzeug.security import check_password_hash

from src.database import get_db


def _to_dict(row):
    if row is None:
        return None
    return {
        "id": row["id"],
        "nome": row["nome"],
        "email": row["email"],
        "tipo": row["tipo"],
        "criado_em": row["criado_em"],
    }


def find_all():
    db = get_db()
    rows = db.execute("SELECT id, nome, email, tipo, criado_em FROM usuarios").fetchall()
    return [_to_dict(row) for row in rows]


def find_by_id(usuario_id):
    db = get_db()
    row = db.execute(
        "SELECT id, nome, email, tipo, criado_em FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()
    return _to_dict(row)


def find_by_email_with_senha(email):
    db = get_db()
    return db.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()


def authenticate(email, senha):
    row = find_by_email_with_senha(email)
    if row and check_password_hash(row["senha"], senha):
        return _to_dict(row)
    return None


def create(nome, email, senha_hash, tipo):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
        (nome, email, senha_hash, tipo),
    )
    db.commit()
    return cursor.lastrowid
