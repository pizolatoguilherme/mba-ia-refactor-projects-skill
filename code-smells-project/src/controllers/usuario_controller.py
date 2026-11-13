import logging

from flask import jsonify, request

from src.middlewares.error_handler import NotFoundError, UnauthorizedError
from src.models import usuario_model
from src.validators.usuario_validator import validate_criar_usuario, validate_login

log = logging.getLogger(__name__)


def listar_usuarios():
    usuarios = usuario_model.find_all()
    return jsonify({"dados": usuarios, "sucesso": True}), 200


def buscar_usuario(usuario_id):
    usuario = usuario_model.find_by_id(usuario_id)
    if not usuario:
        raise NotFoundError("Usuário não encontrado")
    return jsonify({"dados": usuario, "sucesso": True}), 200


def criar_usuario():
    dados = validate_criar_usuario(request.get_json(silent=True))
    usuario_id = usuario_model.create(**dados)
    log.info("Usuário criado: %s", dados["email"])
    return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201


def login():
    email, senha = validate_login(request.get_json(silent=True))

    usuario = usuario_model.authenticate(email, senha)
    if usuario:
        log.info("Login bem-sucedido: %s", email)
        return jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}), 200

    log.info("Login falhou: %s", email)
    raise UnauthorizedError("Email ou senha inválidos", sucesso=False)
