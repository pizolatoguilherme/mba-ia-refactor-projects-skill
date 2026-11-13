from datetime import datetime

from config.settings import (
    VALID_STATUSES, MIN_TITLE_LENGTH, MAX_TITLE_LENGTH, MIN_PRIORITY, MAX_PRIORITY,
)
from middlewares.error_handler import ValidationError


def check_title_length(title):
    if len(title) < MIN_TITLE_LENGTH:
        raise ValidationError('Título muito curto')
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError('Título muito longo')


def check_status(status):
    if status not in VALID_STATUSES:
        raise ValidationError('Status inválido')


def check_priority(priority):
    if not isinstance(priority, (int, float)) or isinstance(priority, bool):
        raise ValidationError('Prioridade deve ser entre 1 e 5')
    if priority < MIN_PRIORITY or priority > MAX_PRIORITY:
        raise ValidationError('Prioridade deve ser entre 1 e 5')


def parse_due_date(due_date, invalid_message):
    try:
        return datetime.strptime(due_date, '%Y-%m-%d')
    except (TypeError, ValueError):
        raise ValidationError(invalid_message)


def normalize_tags(tags):
    if isinstance(tags, list):
        return ','.join(tags)
    return tags


def validate_create(data):
    if not data:
        raise ValidationError('Dados inválidos')

    title = data.get('title')
    if not title:
        raise ValidationError('Título é obrigatório')
    check_title_length(title)

    status = data.get('status', 'pending')
    check_status(status)

    priority = data.get('priority', 3)
    check_priority(priority)

    due_date = None
    if data.get('due_date'):
        due_date = parse_due_date(data['due_date'], 'Formato de data inválido. Use YYYY-MM-DD')

    return {
        'title': title,
        'description': data.get('description', ''),
        'status': status,
        'priority': priority,
        'user_id': data.get('user_id'),
        'category_id': data.get('category_id'),
        'due_date': due_date,
        'tags': normalize_tags(data.get('tags')),
    }


def validate_update(data):
    if not data:
        raise ValidationError('Dados inválidos')

    updates = {}

    if 'title' in data:
        title = data['title']
        if not title:
            raise ValidationError('Título muito curto')
        check_title_length(title)
        updates['title'] = title

    if 'description' in data:
        updates['description'] = data['description']

    if 'status' in data:
        check_status(data['status'])
        updates['status'] = data['status']

    if 'priority' in data:
        check_priority(data['priority'])
        updates['priority'] = data['priority']

    if 'user_id' in data:
        updates['user_id'] = data['user_id']

    if 'category_id' in data:
        updates['category_id'] = data['category_id']

    if 'due_date' in data:
        updates['due_date'] = (
            parse_due_date(data['due_date'], 'Formato de data inválido') if data['due_date'] else None
        )

    if 'tags' in data:
        updates['tags'] = normalize_tags(data['tags'])

    return updates
