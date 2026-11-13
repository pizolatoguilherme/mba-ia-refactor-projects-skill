from src.config.settings import STATUS_PEDIDO_VALIDOS
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

    return usuario_id, itens


def validate_status(dados):
    novo_status = (dados or {}).get("status", "")
    if novo_status not in STATUS_PEDIDO_VALIDOS:
        raise ValidationError("Status inválido")
    return novo_status
