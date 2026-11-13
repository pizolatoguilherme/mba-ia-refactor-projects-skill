import logging

from flask import Flask
from flask_cors import CORS

from src.config.settings import Settings
from src.database import init_app as init_db
from src.middlewares.error_handler import register_error_handlers
from src.views.admin_routes import admin_bp
from src.views.main_routes import main_bp
from src.views.pedido_routes import pedido_bp
from src.views.produto_routes import produto_bp
from src.views.relatorio_routes import relatorio_bp
from src.views.usuario_routes import usuario_bp


def create_app(settings=Settings):
    logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO)

    app = Flask(__name__)
    app.config.from_object(settings)
    CORS(app, origins=settings.CORS_ORIGINS)

    register_error_handlers(app)
    init_db(app)

    for bp in (main_bp, produto_bp, usuario_bp, pedido_bp, relatorio_bp, admin_bp):
        app.register_blueprint(bp)

    return app
