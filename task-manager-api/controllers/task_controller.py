import logging
from datetime import datetime

from flask import jsonify, request

from config.settings import (
    DEFAULT_PRIORITY,
    MAX_TITLE_LENGTH,
    MIN_TITLE_LENGTH,
    PRIORITY_MAX,
    PRIORITY_MIN,
    VALID_STATUSES,
)
from database import db
from middlewares.error_handler import AppError, NotFoundError, ValidationError
from models.category import Category
from models.task import Task
from models.user import User
from utils.helpers import calculate_percentage
from utils.time import utcnow

log = logging.getLogger(__name__)


def _serialize(task):
    data = task.to_dict()
    data['overdue'] = task.is_overdue()
    return data


def _serialize_with_names(task):
    data = _serialize(task)
    data['user_name'] = task.user.name if task.user else None
    data['category_name'] = task.category.name if task.category else None
    return data


def _validate_title(title):
    if not title:
        raise ValidationError('Título é obrigatório')
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError('Título muito longo')


def _validate_status(status):
    if status not in VALID_STATUSES:
        raise ValidationError('Status inválido')


def _validate_priority(priority):
    if not isinstance(priority, int) or priority < PRIORITY_MIN or priority > PRIORITY_MAX:
        raise ValidationError('Prioridade deve ser entre 1 e 5')


def _normalize_tags(tags):
    if isinstance(tags, list):
        return ','.join(tags)
    return tags


def list_tasks():
    tasks = Task.find_all_with_relations()
    return jsonify([_serialize_with_names(t) for t in tasks]), 200


def get_task(task_id):
    task = Task.find_by_id(task_id)
    if not task:
        raise NotFoundError('Task não encontrada')
    return jsonify(_serialize(task)), 200


def create_task():
    data = request.get_json(silent=True)
    if not data:
        raise ValidationError('Dados inválidos')

    title = data.get('title')
    _validate_title(title)

    status = data.get('status', 'pending')
    _validate_status(status)

    priority = data.get('priority', DEFAULT_PRIORITY)
    _validate_priority(priority)

    user_id = data.get('user_id')
    if user_id and not User.find_by_id(user_id):
        raise NotFoundError('Usuário não encontrado')

    category_id = data.get('category_id')
    if category_id and not Category.find_by_id(category_id):
        raise NotFoundError('Categoria não encontrada')

    task = Task()
    task.title = title
    task.description = data.get('description', '')
    task.status = status
    task.priority = priority
    task.user_id = user_id
    task.category_id = category_id

    due_date = data.get('due_date')
    if due_date:
        try:
            task.due_date = datetime.strptime(due_date, '%Y-%m-%d')
        except ValueError:
            raise ValidationError('Formato de data inválido. Use YYYY-MM-DD')

    tags = data.get('tags')
    if tags:
        task.tags = _normalize_tags(tags)

    try:
        db.session.add(task)
        db.session.commit()
    except Exception:
        db.session.rollback()
        log.exception('Erro ao criar task')
        raise AppError('Erro ao criar task', 500)

    log.info('Task criada: %s - %s', task.id, task.title)
    return jsonify(task.to_dict()), 201


def update_task(task_id):
    task = Task.find_by_id(task_id)
    if not task:
        raise NotFoundError('Task não encontrada')

    data = request.get_json(silent=True)
    if not data:
        raise ValidationError('Dados inválidos')

    if 'title' in data:
        title = data['title']
        if len(title) < MIN_TITLE_LENGTH:
            raise ValidationError('Título muito curto')
        if len(title) > MAX_TITLE_LENGTH:
            raise ValidationError('Título muito longo')
        task.title = title

    if 'description' in data:
        task.description = data['description']

    if 'status' in data:
        _validate_status(data['status'])
        task.status = data['status']

    if 'priority' in data:
        _validate_priority(data['priority'])
        task.priority = data['priority']

    if 'user_id' in data:
        if data['user_id'] and not User.find_by_id(data['user_id']):
            raise NotFoundError('Usuário não encontrado')
        task.user_id = data['user_id']

    if 'category_id' in data:
        if data['category_id'] and not Category.find_by_id(data['category_id']):
            raise NotFoundError('Categoria não encontrada')
        task.category_id = data['category_id']

    if 'due_date' in data:
        if data['due_date']:
            try:
                task.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d')
            except ValueError:
                raise ValidationError('Formato de data inválido')
        else:
            task.due_date = None

    if 'tags' in data:
        task.tags = _normalize_tags(data['tags'])

    task.updated_at = utcnow()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise AppError('Erro ao atualizar', 500)

    log.info('Task atualizada: %s', task.id)
    return jsonify(task.to_dict()), 200


def delete_task(task_id):
    task = Task.find_by_id(task_id)
    if not task:
        raise NotFoundError('Task não encontrada')

    try:
        db.session.delete(task)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise AppError('Erro ao deletar', 500)

    log.info('Task deletada: %s', task_id)
    return jsonify({'message': 'Task deletada com sucesso'}), 200


def search_tasks():
    query = request.args.get('q', '')
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')
    user_id = request.args.get('user_id', '')

    tasks = Task.search(
        query=query or None,
        status=status or None,
        priority=int(priority) if priority else None,
        user_id=int(user_id) if user_id else None,
    )
    return jsonify([t.to_dict() for t in tasks]), 200


def task_stats():
    counts = Task.count_by_status()
    total = sum(counts.values())
    done = counts.get('done', 0)
    overdue_count = len(Task.find_overdue())

    stats = {
        'total': total,
        'pending': counts.get('pending', 0),
        'in_progress': counts.get('in_progress', 0),
        'done': done,
        'cancelled': counts.get('cancelled', 0),
        'overdue': overdue_count,
        'completion_rate': calculate_percentage(done, total),
    }
    return jsonify(stats), 200
