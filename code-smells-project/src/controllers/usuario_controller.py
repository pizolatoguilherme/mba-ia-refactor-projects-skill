from flask import jsonify, request
from werkzeug.security import generate_password_hash

from src.config.settings import TIPO_USUARIO_PADRAO
from src.middlewares.error_handler import NotFoundError, UnauthorizedError
from src.models import usuario_model
from src.validators.usuario_validator import validate_criar_usuario, validate_login


def listar_usuarios():
    usuarios = usuario_model.find_all()
    return jsonify({"dados": usuarios, "sucesso": True}), 200


def buscar_usuario(id):
    usuario = usuario_model.find_by_id(id)
    if not usuario:
        raise NotFoundError("Usuário não encontrado")
    return jsonify({"dados": usuario, "sucesso": True}), 200


def criar_usuario():
    dados = validate_criar_usuario(request.get_json(silent=True))
    senha_hash = generate_password_hash(dados["senha"])
    usuario_id = usuario_model.create(dados["nome"], dados["email"], senha_hash, TIPO_USUARIO_PADRAO)
    return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201


def login():
    email, senha = validate_login(request.get_json(silent=True))

    usuario = usuario_model.authenticate(email, senha)
    if usuario:
        return jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}), 200

    raise UnauthorizedError("Email ou senha inválidos")
