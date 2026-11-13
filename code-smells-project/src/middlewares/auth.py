import hmac
from functools import wraps

from flask import request

from src.config.settings import Settings
from src.middlewares.error_handler import ForbiddenError


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-Admin-Token", "")
        if not Settings.ADMIN_TOKEN or not hmac.compare_digest(token, Settings.ADMIN_TOKEN):
            raise ForbiddenError("Acesso restrito a administradores")
        return fn(*args, **kwargs)

    return wrapper
