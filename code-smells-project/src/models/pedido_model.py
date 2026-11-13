from src.database import get_db
from src.models import produto_model


def _fetch_pedidos(usuario_id=None):
    db = get_db()
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
    rows = db.execute(query, (usuario_id, usuario_id)).fetchall()

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
            pedidos[pedido_id]["itens"].append({
                "produto_id": row["produto_id"],
                "produto_nome": row["produto_nome"],
                "quantidade": row["quantidade"],
                "preco_unitario": row["preco_unitario"],
            })
    return list(pedidos.values())


def find_all():
    return _fetch_pedidos()


def find_by_usuario(usuario_id):
    return _fetch_pedidos(usuario_id)


def create(usuario_id, itens):
    db = get_db()

    produtos_por_id = {}
    total = 0
    for item in itens:
        produto = produto_model.find_by_id(item["produto_id"])
        if produto is None:
            return {"erro": f"Produto {item['produto_id']} não encontrado"}
        if produto["estoque"] < item["quantidade"]:
            return {"erro": f"Estoque insuficiente para {produto['nome']}"}
        produtos_por_id[item["produto_id"]] = produto
        total += produto["preco"] * item["quantidade"]

    with db:
        cursor = db.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, 'pendente', ?)",
            (usuario_id, total),
        )
        pedido_id = cursor.lastrowid

        for item in itens:
            produto = produtos_por_id[item["produto_id"]]
            db.execute(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) "
                "VALUES (?, ?, ?, ?)",
                (pedido_id, item["produto_id"], item["quantidade"], produto["preco"]),
            )
            produto_model.decrement_estoque(item["produto_id"], item["quantidade"])

    return {"pedido_id": pedido_id, "total": total}


def update_status(pedido_id, novo_status):
    db = get_db()
    db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id))
    db.commit()


def contagem_por_status(status):
    db = get_db()
    row = db.execute("SELECT COUNT(*) FROM pedidos WHERE status = ?", (status,)).fetchone()
    return row[0]


def totais():
    db = get_db()
    row = db.execute("SELECT COUNT(*), SUM(total) FROM pedidos").fetchone()
    total_pedidos, faturamento = row[0], row[1]
    return total_pedidos, (faturamento or 0)
