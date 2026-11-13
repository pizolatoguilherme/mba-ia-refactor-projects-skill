import logging
import os
import secrets

log = logging.getLogger(__name__)


def _bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ('1', 'true', 'yes')


class Settings:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    DEBUG = _bool('FLASK_DEBUG', False)
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', '5000'))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///tasks.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')


if not os.environ.get('SECRET_KEY'):
    log.warning('SECRET_KEY não definida; usando uma chave efêmera gerada em memória')

VALID_STATUSES = ['pending', 'in_progress', 'done', 'cancelled']
CLOSED_STATUSES = ['done', 'cancelled']
VALID_ROLES = ['user', 'admin', 'manager']
DEFAULT_ROLE = 'user'
MAX_TITLE_LENGTH = 200
MIN_TITLE_LENGTH = 3
MIN_PASSWORD_LENGTH = 4
DEFAULT_PRIORITY = 3
PRIORITY_MIN = 1
PRIORITY_MAX = 5
DEFAULT_COLOR = '#000000'
