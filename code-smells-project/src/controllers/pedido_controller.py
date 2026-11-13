from flask import jsonify, request

from src.config.settings import STATUS_PEDIDO_VALIDOS
from src.middlewares.error_handler import ValidationError
from src.models import pedido_model
from src.services import notification_service
from src.validators.pedido_validator import validate_criar_pedido, validate_status


def criar_pedido():
    usuario_id, itens = validate_criar_pedido(request.get_json(silent=True))

    resultado = pedido_model.create(usuario_id, itens)
    if "erro" in resultado:
        raise ValidationError(resultado["erro"])

    notification_service.pedido_criado(resultado["pedido_id"], usuario_id)

    return jsonify(
        {"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}
    ), 201


def listar_pedidos_usuario(usuario_id):
    pedidos = pedido_model.find_by_usuario(usuario_id)
    return jsonify({"dados": pedidos, "sucesso": True}), 200


def listar_todos_pedidos():
    pedidos = pedido_model.find_all()
    return jsonify({"dados": pedidos, "sucesso": True}), 200


def atualizar_status_pedido(pedido_id):
    novo_status = validate_status(request.get_json(silent=True), STATUS_PEDIDO_VALIDOS)

    pedido_model.update_status(pedido_id, novo_status)
    notification_service.pedido_status_alterado(pedido_id, novo_status)

    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
