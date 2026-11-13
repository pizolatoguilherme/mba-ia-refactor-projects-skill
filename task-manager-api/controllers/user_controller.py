import logging

from flask import jsonify
from sqlalchemy.orm import joinedload

from database import db
from models.user import User
from models.task import Task
from middlewares.error_handler import (
    NotFoundError, UnauthorizedError, ForbiddenError, ConflictError, AppError,
)
from validators.user_validator import validate_create, validate_update
from config.settings import DEFAULT_ROLE

logger = logging.getLogger(__name__)


def list_users():
    users = User.query.options(joinedload(User.tasks)).all()
    result = []
    for u in users:
        data = u.to_dict()
        data['task_count'] = len(u.tasks)
        result.append(data)
    return jsonify(result), 200


def get_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')

    data = user.to_dict()
    tasks = Task.query.filter_by(user_id=user_id).all()
    data['tasks'] = [t.to_dict() for t in tasks]
    return jsonify(data), 200


def create_user(payload):
    fields = validate_create(payload)

    existing = User.query.filter_by(email=fields['email']).first()
    if existing:
        raise ConflictError('Email já cadastrado')

    user = User()
    user.name = fields['name']
    user.email = fields['email']
    user.set_password(fields['password'])
    # role enviada pelo cliente é ignorada: cadastro público nunca cria admin/manager
    user.role = DEFAULT_ROLE

    try:
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('Erro ao criar usuário')
        raise AppError('Erro ao criar usuário', 500)

    logger.info('Usuário criado: %s - %s', user.id, user.name)
    return jsonify(user.to_dict()), 201


def update_user(user_id, payload):
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')

    updates = validate_update(payload)

    if 'email' in updates:
        existing = User.query.filter_by(email=updates['email']).first()
        if existing and existing.id != user_id:
            raise ConflictError('Email já cadastrado')
        user.email = updates['email']

    if 'name' in updates:
        user.name = updates['name']
    if 'password' in updates:
        user.set_password(updates['password'])
    if 'role' in updates:
        user.role = updates['role']
    if 'active' in updates:
        user.active = updates['active']

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('Erro ao atualizar usuário')
        raise AppError('Erro ao atualizar', 500)

    return jsonify(user.to_dict()), 200


def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')

    Task.query.filter_by(user_id=user_id).delete()

    try:
        db.session.delete(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('Erro ao deletar usuário')
        raise AppError('Erro ao deletar', 500)

    logger.info('Usuário deletado: %s', user_id)
    return jsonify({'message': 'Usuário deletado com sucesso'}), 200


def get_user_tasks(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError('Usuário não encontrado')

    tasks = Task.query.filter_by(user_id=user_id).all()
    result = [
        {
            'id': t.id,
            'title': t.title,
            'description': t.description,
            'status': t.status,
            'priority': t.priority,
            'created_at': str(t.created_at),
            'due_date': str(t.due_date) if t.due_date else None,
            'overdue': t.is_overdue(),
        }
        for t in tasks
    ]
    return jsonify(result), 200


def login(payload):
    if not payload:
        raise AppError('Dados inválidos', 400)

    email = payload.get('email')
    password = payload.get('password')

    if not email or not password:
        raise AppError('Email e senha são obrigatórios', 400)

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        raise UnauthorizedError('Credenciais inválidas')

    if not user.active:
        raise ForbiddenError('Usuário inativo')

    return jsonify({
        'message': 'Login realizado com sucesso',
        'user': user.to_dict(),
        'token': 'fake-jwt-token-' + str(user.id),
    }), 200
