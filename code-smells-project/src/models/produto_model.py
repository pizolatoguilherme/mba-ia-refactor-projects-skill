from src.database import get_db

COLUMNS = "id, nome, descricao, preco, estoque, categoria, ativo, criado_em"


def _to_dict(row):
    return dict(row) if row else None


def find_all():
    rows = get_db().execute(f"SELECT {COLUMNS} FROM produtos").fetchall()
    return [_to_dict(r) for r in rows]


def find_by_id(produto_id):
    row = get_db().execute(f"SELECT {COLUMNS} FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    return _to_dict(row)


def search(termo=None, categoria=None, preco_min=None, preco_max=None):
    clauses, params = ["1=1"], []
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
    rows = get_db().execute(query, params).fetchall()
    return [_to_dict(r) for r in rows]


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


def delete(produto_id):
    db = get_db()
    db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
    db.commit()


def has_pedidos(produto_id):
    row = get_db().execute(
        "SELECT COUNT(*) FROM itens_pedido WHERE produto_id = ?", (produto_id,)
    ).fetchone()
    return row[0] > 0


def decrement_estoque(produto_id, quantidade):
    get_db().execute(
        "UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (quantidade, produto_id)
    )


def count():
    return get_db().execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
