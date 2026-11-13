from src.database import get_db

COLUMNS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


def _to_dict(row):
    if row is None:
        return None
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def find_all():
    db = get_db()
    rows = db.execute(f"SELECT {COLUMNS} FROM produtos").fetchall()
    return [_to_dict(row) for row in rows]


def find_by_id(produto_id):
    db = get_db()
    row = db.execute(f"SELECT {COLUMNS} FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    return _to_dict(row)


def search(termo=None, categoria=None, preco_min=None, preco_max=None):
    db = get_db()
    clauses = ["1=1"]
    params = []

    if termo:
        clauses.append("(nome LIKE ? OR descricao LIKE ?)")
        params += [f"%{termo}%", f"%{termo}%"]
    if categoria:
        clauses.append("categoria = ?")
        params.append(categoria)
    if preco_min is not None:
        clauses.append("preco >= ?")
        params.append(preco_min)
    if preco_max is not None:
        clauses.append("preco <= ?")
        params.append(preco_max)

    query = f"SELECT {COLUMNS} FROM produtos WHERE {' AND '.join(clauses)}"
    rows = db.execute(query, params).fetchall()
    return [_to_dict(row) for row in rows]


def create(nome, descricao, preco, estoque, categoria):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
        (nome, descricao, preco, estoque, categoria),
    )
    db.commit()
    return cursor.lastrowid


def update(produto_id, nome, descricao, preco, estoque, categoria):
    db = get_db()
    db.execute(
        "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
        (nome, descricao, preco, estoque, categoria, produto_id),
    )
    db.commit()


def has_pedidos(produto_id):
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) FROM itens_pedido WHERE produto_id = ?", (produto_id,)
    ).fetchone()
    return row[0] > 0


def deactivate(produto_id):
    db = get_db()
    db.execute("UPDATE produtos SET ativo = 0 WHERE id = ?", (produto_id,))
    db.commit()


def delete(produto_id):
    db = get_db()
    db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    db.commit()


def decrement_estoque(produto_id, quantidade):
    db = get_db()
    db.execute(
        "UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (quantidade, produto_id)
    )
