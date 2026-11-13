import logging

from flask import jsonify
from sqlalchemy.orm import joinedload

from database import db
from models.task import Task
from models.user import User
from models.category import Category
from middlewares.error_handler import NotFoundError, ValidationError, AppError
from utils.time import utcnow
from validators.task_validator import validate_create, validate_update

logger = logging.getLogger(__name__)


def _check_foreign_keys(user_id=None, category_id=None):
    if user_id and not db.session.get(User, user_id):
        raise NotFoundError('Usuário não encontrado')
    if category_id and not db.session.get(Category, category_id):
        raise NotFoundError('Categoria não encontrada')


def _serialize_with_relations(task):
    data = task.to_dict()
    data['overdue'] = task.is_overdue()
    data['user_name'] = task.user.name if task.user else None
    data['category_name'] = task.category.name if task.category else None
    return data


def list_tasks():
    tasks = Task.query.options(joinedload(Task.user), joinedload(Task.category)).all()
    return jsonify([_serialize_with_relations(t) for t in tasks]), 200


def get_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    data = task.to_dict()
    data['overdue'] = task.is_overdue()
    return jsonify(data), 200


def create_task(payload):
    fields = validate_create(payload)
    _check_foreign_keys(fields['user_id'], fields['category_id'])

    task = Task()
    task.title = fields['title']
    task.description = fields['description']
    task.status = fields['status']
    task.priority = fields['priority']
    task.user_id = fields['user_id']
    task.category_id = fields['category_id']
    task.due_date = fields['due_date']
    task.tags = fields['tags']

    try:
        db.session.add(task)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('Erro ao criar task')
        raise AppError('Erro ao criar task', 500)

    logger.info('Task criada: %s - %s', task.id, task.title)
    return jsonify(task.to_dict()), 201


def update_task(task_id, payload):
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError('Task não encontrada')

    updates = validate_update(payload)
    _check_foreign_keys(updates.get('user_id'), updates.get('category_id'))

    for field, value in updates.items():
        setattr(task, field, value)
    task.updated_at = utcnow()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('Erro ao atualizar task')
        raise AppError('Erro ao atualizar', 500)

    logger.info('Task atualizada: %s', task.id)
    return jsonify(task.to_dict()), 200


def delete_task(task_id):
    task = db.session.get(Task, task_id)
    if not task:
        raise NotFoundError('Task não encontrada')

    try:
        db.session.delete(task)
        db.session.commit()
    except Exception:
        db.session.rollback()
        logger.exception('Erro ao deletar task')
        raise AppError('Erro ao deletar', 500)

    logger.info('Task deletada: %s', task_id)
    return jsonify({'message': 'Task deletada com sucesso'}), 200


def search_tasks(args):
    query = args.get('q', '')
    status = args.get('status', '')
    priority = args.get('priority', '')
    user_id = args.get('user_id', '')

    tasks = Task.query

    if query:
        tasks = tasks.filter(
            db.or_(Task.title.like(f'%{query}%'), Task.description.like(f'%{query}%'))
        )
    if status:
        tasks = tasks.filter(Task.status == status)
    if priority:
        try:
            tasks = tasks.filter(Task.priority == int(priority))
        except ValueError:
            raise ValidationError('Prioridade inválida')
    if user_id:
        try:
            tasks = tasks.filter(Task.user_id == int(user_id))
        except ValueError:
            raise ValidationError('user_id inválido')

    results = tasks.all()
    return jsonify([t.to_dict() for t in results]), 200


def task_stats():
    counts = dict(
        db.session.query(Task.status, db.func.count(Task.id)).group_by(Task.status).all()
    )
    total = sum(counts.values())
    overdue_count = sum(1 for t in Task.query.all() if t.is_overdue())

    stats = {
        'total': total,
        'pending': counts.get('pending', 0),
        'in_progress': counts.get('in_progress', 0),
        'done': counts.get('done', 0),
        'cancelled': counts.get('cancelled', 0),
        'overdue': overdue_count,
        'completion_rate': round((counts.get('done', 0) / total) * 100, 2) if total > 0 else 0,
    }
    return jsonify(stats), 200
