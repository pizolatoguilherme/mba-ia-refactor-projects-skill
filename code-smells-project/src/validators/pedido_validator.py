from src.middlewares.error_handler import ValidationError


def validate_criar_pedido(dados):
    if not dados:
        raise ValidationError("Dados inválidos")

    usuario_id = dados.get("usuario_id")
    itens = dados.get("itens", [])

    if not usuario_id:
        raise ValidationError("Usuario ID é obrigatório")
    if not itens or len(itens) == 0:
        raise ValidationError("Pedido deve ter pelo menos 1 item")

    for item in itens:
        if not isinstance(item, dict) or "produto_id" not in item or "quantidade" not in item:
            raise ValidationError("Cada item do pedido precisa de produto_id e quantidade")

    return usuario_id, itens


def validate_status(dados, status_validos):
    if not dados:
        raise ValidationError("Status inválido")

    novo_status = dados.get("status", "")
    if novo_status not in status_validos:
        raise ValidationError("Status inválido")

    return novo_status
