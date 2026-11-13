from src.database import get_db
from src.middlewares.error_handler import ValidationError
from src.models import pedido_model, produto_model
from src.services import notification_service


def criar_pedido(usuario_id, itens):
    produtos_por_item = []
    total = 0
    for item in itens:
        produto_id = item.get("produto_id")
        quantidade = item.get("quantidade")
        if produto_id is None or quantidade is None:
            raise ValidationError("Cada item deve ter produto_id e quantidade", sucesso=False)

        produto = produto_model.find_by_id(produto_id)
        if produto is None:
            raise ValidationError(f"Produto {produto_id} não encontrado", sucesso=False)
        if produto["estoque"] < quantidade:
            raise ValidationError(f"Estoque insuficiente para {produto['nome']}", sucesso=False)

        produtos_por_item.append((produto, quantidade))
        total += produto["preco"] * quantidade

    db = get_db()
    with db:
        pedido_id = pedido_model.insert_pedido(usuario_id, total)
        for produto, quantidade in produtos_por_item:
            pedido_model.insert_item(pedido_id, produto["id"], quantidade, produto["preco"])
            produto_model.decrement_estoque(produto["id"], quantidade)

    notification_service.pedido_criado(pedido_id, usuario_id)
    return {"pedido_id": pedido_id, "total": total}
