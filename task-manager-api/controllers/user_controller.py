import logging

from flask import jsonify, request

from config.settings import DEFAULT_ROLE, MIN_PASSWORD_LENGTH, VALID_ROLES
from database import db
from middlewares.error_handler import (
    AppError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)
from models.task import Task
from models.user import User
from utils.helpers import validate_email

log = logging.getLogger(__name__)


def list_users():
    users = User.query.all()
    task_counts = Task.count_by_user()
    result = []
    for u in users:
        user_data = u.to_dict()
        user_data['task_count'] = task_counts.get(u.id, 0)
        result.append(user_data)
    return jsonify(result), 200


def get_user(user_id):
    user = User.find_by_id(user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')

    data = user.to_dict()
    data['tasks'] = [t.to_dict() for t in Task.query.filter_by(user_id=user_id).all()]
    return jsonify(data), 200


def create_user():
    data = request.get_json(silent=True)
    if not data:
        raise ValidationError('Dados inválidos')

    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not name:
        raise ValidationError('Nome é obrigatório')
    if not email:
        raise ValidationError('Email é obrigatório')
    if not password:
        raise ValidationError('Senha é obrigatória')
    if not validate_email(email):
        raise ValidationError('Email inválido')
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError('Senha deve ter no mínimo 4 caracteres')
    if User.find_by_email(email):
        raise ConflictError('Email já cadastrado')

    user = User()
    user.name = name
    user.email = email
    user.set_password(password)
    user.role = DEFAULT_ROLE  # role vinda do cliente é ignorada para evitar escalonamento de privilégio

    try:
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        log.exception('Erro ao criar usuário')
        raise AppError('Erro ao criar usuário', 500)

    log.info('Usuário criado: %s - %s', user.id, user.name)
    return jsonify(user.to_dict()), 201


def update_user(user_id):
    user = User.find_by_id(user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')

    data = request.get_json(silent=True)
    if not data:
        raise ValidationError('Dados inválidos')

    if 'name' in data:
        user.name = data['name']

    if 'email' in data:
        if not validate_email(data['email']):
            raise ValidationError('Email inválido')
        existing = User.find_by_email(data['email'])
        if existing and existing.id != user_id:
            raise ConflictError('Email já cadastrado')
        user.email = data['email']

    if 'password' in data:
        if len(data['password']) < MIN_PASSWORD_LENGTH:
            raise ValidationError('Senha muito curta')
        user.set_password(data['password'])

    if 'role' in data:
        if data['role'] not in VALID_ROLES:
            raise ValidationError('Role inválido')
        user.role = data['role']

    if 'active' in data:
        user.active = data['active']

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise AppError('Erro ao atualizar', 500)

    return jsonify(user.to_dict()), 200


def delete_user(user_id):
    user = User.find_by_id(user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')

    try:
        Task.query.filter_by(user_id=user_id).delete()
        db.session.delete(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise AppError('Erro ao deletar', 500)

    log.info('Usuário deletado: %s', user_id)
    return jsonify({'message': 'Usuário deletado com sucesso'}), 200


def get_user_tasks(user_id):
    user = User.find_by_id(user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')

    tasks = Task.query.filter_by(user_id=user_id).all()
    result = []
    for t in tasks:
        result.append({
            'id': t.id,
            'title': t.title,
            'description': t.description,
            'status': t.status,
            'priority': t.priority,
            'created_at': str(t.created_at),
            'due_date': str(t.due_date) if t.due_date else None,
            'overdue': t.is_overdue(),
        })
    return jsonify(result), 200


def login():
    data = request.get_json(silent=True)
    if not data:
        raise ValidationError('Dados inválidos')

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        raise ValidationError('Email e senha são obrigatórios')

    user = User.find_by_email(email)
    if not user:
        raise UnauthorizedError('Credenciais inválidas')

    if not user.check_password(password):
        raise UnauthorizedError('Credenciais inválidas')

    if not user.active:
        raise ForbiddenError('Usuário inativo')

    return jsonify({
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': 'fake-jwt-token-' + str(user.id),
    }), 200
