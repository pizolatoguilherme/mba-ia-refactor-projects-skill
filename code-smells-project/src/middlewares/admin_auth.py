import hmac
from functools import wraps

from flask import request, current_app

from src.middlewares.error_handler import ForbiddenError


def require_admin(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        admin_token = current_app.config.get("ADMIN_TOKEN")
        token = request.headers.get("X-Admin-Token", "")
        if not admin_token or not hmac.compare_digest(token, admin_token):
            raise ForbiddenError("Acesso restrito a administradores")
        return fn(*args, **kwargs)

    return wrapper
