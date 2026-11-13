import re

from config.settings import VALID_ROLES, MIN_PASSWORD_LENGTH
from middlewares.error_handler import ValidationError

EMAIL_RE = re.compile(r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$')


def check_email_format(email):
    if not EMAIL_RE.match(email):
        raise ValidationError('Email inválido')


def check_password_length(password, message):
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationError(message)


def check_role(role):
    if role not in VALID_ROLES:
        raise ValidationError('Role inválido')


def validate_create(data):
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

    check_email_format(email)
    check_password_length(password, 'Senha deve ter no mínimo 4 caracteres')

    return {'name': name, 'email': email, 'password': password}


def validate_update(data):
    if not data:
        raise ValidationError('Dados inválidos')

    updates = {}
    if 'name' in data:
        updates['name'] = data['name']
    if 'email' in data:
        check_email_format(data['email'])
        updates['email'] = data['email']
    if 'password' in data:
        check_password_length(data['password'], 'Senha muito curta')
        updates['password'] = data['password']
    if 'role' in data:
        check_role(data['role'])
        updates['role'] = data['role']
    if 'active' in data:
        updates['active'] = data['active']
    return updates
