import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

log = logging.getLogger(__name__)


class AppError(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, **extra):
        super().__init__(message)
        self.message = message
        if status_code:
            self.status_code = status_code
        self.extra = extra


class ValidationError(AppError):
    status_code = 400


class UnauthorizedError(AppError):
    status_code = 401


class ForbiddenError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        return jsonify({"erro": err.message, **err.extra}), err.status_code

    @app.errorhandler(HTTPException)
    def handle_http(err):
        return jsonify({"erro": err.description}), err.code

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        log.exception("Erro não tratado")
        return jsonify({"erro": "Erro interno do servidor"}), 500
