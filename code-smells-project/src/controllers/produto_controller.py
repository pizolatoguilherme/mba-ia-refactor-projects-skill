from flask import jsonify, request

from src.middlewares.error_handler import NotFoundError
from src.models import produto_model
from src.validators.produto_validator import validate_produto


def listar_produtos():
    produtos = produto_model.find_all()
    return jsonify({"dados": produtos, "sucesso": True}), 200


def buscar_produto(id):
    produto = produto_model.find_by_id(id)
    if not produto:
        raise NotFoundError("Produto não encontrado")
    return jsonify({"dados": produto, "sucesso": True}), 200


def criar_produto():
    dados = validate_produto(request.get_json(silent=True))
    produto_id = produto_model.create(**dados)
    return jsonify(
        {"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}
    ), 201


def atualizar_produto(id):
    produto_existente = produto_model.find_by_id(id)
    if not produto_existente:
        raise NotFoundError("Produto não encontrado")

    dados = validate_produto(request.get_json(silent=True))
    produto_model.update(id, **dados)
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


def deletar_produto(id):
    produto = produto_model.find_by_id(id)
    if not produto:
        raise NotFoundError("Produto não encontrado")

    if produto_model.has_pedidos(id):
        produto_model.deactivate(id)
    else:
        produto_model.delete(id)

    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200


def buscar_produtos():
    termo = request.args.get("q", "")
    categoria = request.args.get("categoria", None)
    preco_min = request.args.get("preco_min", None)
    preco_max = request.args.get("preco_max", None)

    if preco_min:
        preco_min = float(preco_min)
    if preco_max:
        preco_max = float(preco_max)

    resultados = produto_model.search(termo, categoria, preco_min, preco_max)
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200
