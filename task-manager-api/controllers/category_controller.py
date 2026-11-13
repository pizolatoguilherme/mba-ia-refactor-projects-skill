import logging

from flask import jsonify

from database import db
from models.category import Category
from models.task import Task
from middlewares.error_handler import NotFoundError, ValidationError, AppError
from config.settings import DEFAULT_COLOR

logger = logging.getLogger(__name__)


def list_categories():
    categories = Category.query.all()
    result = []
    for c in categories:
        data = c.to_dict()
        data['task_count'] = Task.query.filter_by(category_id=c.id).count()
        result.append(data)
    return jsonify(result), 200


def create_category(payload):
    if not payload:
        raise ValidationError('Dados inválidos')

    name = payload.get('name')
    if not name:
        raise ValidationError('Nome é obrigatório')

    category = Category()
    category.name = name
    category.description = payload.get('description', '')
    category.color = payload.get('color', DEFAULT_COLOR)

    try:
        db.session.add(category)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('Erro ao criar categoria')
        raise AppError('Erro ao criar categoria', 500)

    return jsonify(category.to_dict()), 201


def update_category(cat_id, payload):
    cat = db.session.get(Category, cat_id)
    if not cat:
        raise NotFoundError('Categoria não encontrada')

    if not payload:
        raise ValidationError('Dados inválidos')

    if 'name' in payload:
        cat.name = payload['name']
    if 'description' in payload:
        cat.description = payload['description']
    if 'color' in payload:
        cat.color = payload['color']

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('Erro ao atualizar categoria')
        raise AppError('Erro ao atualizar', 500)

    return jsonify(cat.to_dict()), 200


def delete_category(cat_id):
    cat = db.session.get(Category, cat_id)
    if not cat:
        raise NotFoundError('Categoria não encontrada')

    # evita integridade referencial quebrada: tasks ficam sem categoria em vez de
    # apontar para um category_id inexistente
    Task.query.filter_by(category_id=cat_id).update({'category_id': None})

    try:
        db.session.delete(cat)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('Erro ao deletar categoria')
        raise AppError('Erro ao deletar', 500)

    return jsonify({'message': 'Categoria deletada'}), 200
