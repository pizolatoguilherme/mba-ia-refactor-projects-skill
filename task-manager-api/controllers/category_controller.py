from flask import jsonify, request

from database import db
from middlewares.error_handler import AppError, NotFoundError, ValidationError
from models.category import Category
from models.task import Task


def list_categories():
    categories = Category.query.all()
    result = []
    for c in categories:
        cat_data = c.to_dict()
        cat_data['task_count'] = Task.query.filter_by(category_id=c.id).count()
        result.append(cat_data)
    return jsonify(result), 200


def create_category():
    data = request.get_json(silent=True)
    if not data:
        raise ValidationError('Dados inválidos')

    name = data.get('name')
    if not name:
        raise ValidationError('Nome é obrigatório')

    category = Category()
    category.name = name
    category.description = data.get('description', '')
    category.color = data.get('color', '#000000')

    try:
        db.session.add(category)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise AppError('Erro ao criar categoria', 500)

    return jsonify(category.to_dict()), 201


def update_category(cat_id):
    cat = Category.find_by_id(cat_id)
    if not cat:
        raise NotFoundError('Categoria não encontrada')

    data = request.get_json(silent=True)
    if not data:
        raise ValidationError('Dados inválidos')

    if 'name' in data:
        cat.name = data['name']
    if 'description' in data:
        cat.description = data['description']
    if 'color' in data:
        cat.color = data['color']

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise AppError('Erro ao atualizar', 500)

    return jsonify(cat.to_dict()), 200


def delete_category(cat_id):
    cat = Category.find_by_id(cat_id)
    if not cat:
        raise NotFoundError('Categoria não encontrada')

    try:
        Task.query.filter_by(category_id=cat_id).update({'category_id': None})
        db.session.delete(cat)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise AppError('Erro ao deletar', 500)

    return jsonify({'message': 'Categoria deletada'}), 200
