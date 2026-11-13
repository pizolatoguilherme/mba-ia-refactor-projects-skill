from src.database import get_db


def insert_pedido(usuario_id, total):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)",
        (usuario_id, total),
    )
    return cursor.lastrowid


def insert_item(pedido_id, produto_id, quantidade, preco_unitario):
    get_db().execute(
        "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) VALUES (?, ?, ?, ?)",
        (pedido_id, produto_id, quantidade, preco_unitario),
    )


def _find(usuario_id=None):
    query = """
        SELECT p.id AS pedido_id, p.usuario_id, p.status, p.total, p.criado_em,
               i.produto_id, i.quantidade, i.preco_unitario,
               COALESCE(pr.nome, 'Desconhecido') AS produto_nome
        FROM pedidos p
        LEFT JOIN itens_pedido i ON i.pedido_id = p.id
        LEFT JOIN produtos pr ON pr.id = i.produto_id
        WHERE (? IS NULL OR p.usuario_id = ?)
        ORDER BY p.id
    """
    rows = get_db().execute(query, (usuario_id, usuario_id)).fetchall()

    pedidos = {}
    for row in rows:
        pedido_id = row["pedido_id"]
        if pedido_id not in pedidos:
            pedidos[pedido_id] = {
                "id": pedido_id,
                "usuario_id": row["usuario_id"],
                "status": row["status"],
                "total": row["total"],
                "criado_em": row["criado_em"],
                "itens": [],
            }
        if row["produto_id"] is not None:
            pedidos[pedido_id]["itens"].append(
                {
                    "produto_id": row["produto_id"],
                    "produto_nome": row["produto_nome"],
                    "quantidade": row["quantidade"],
                    "preco_unitario": row["preco_unitario"],
                }
            )
    return list(pedidos.values())


def find_all():
    return _find()


def find_by_usuario(usuario_id):
    return _find(usuario_id)


def update_status(pedido_id, novo_status):
    db = get_db()
    db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
    db.commit()


def count():
    return get_db().execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]


def aggregate_vendas():
    db = get_db()
    total_pedidos = db.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    faturamento = db.execute("SELECT SUM(total) FROM pedidos").fetchone()[0] or 0

    contagem_status = dict(
        db.execute("SELECT status, COUNT(*) FROM pedidos GROUP BY status").fetchall()
    )

    return {
        "total_pedidos": total_pedidos,
        "faturamento": faturamento,
        "pendentes": contagem_status.get("pendente", 0),
        "aprovados": contagem_status.get("aprovado", 0),
        "cancelados": contagem_status.get("cancelado", 0),
    }
