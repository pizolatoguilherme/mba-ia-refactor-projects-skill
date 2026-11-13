import logging

from flask import Flask
from flask_cors import CORS

from src.config.settings import Settings
from src.database import init_app as init_database
from src.middlewares.error_handler import register_error_handlers
from src.views.admin_routes import admin_bp
from src.views.health_routes import health_bp
from src.views.home_routes import home_bp
from src.views.pedido_routes import pedido_bp
from src.views.produto_routes import produto_bp
from src.views.relatorio_routes import relatorio_bp
from src.views.usuario_routes import usuario_bp


def create_app(settings=Settings):
    logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO)

    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["DEBUG"] = settings.DEBUG
    app.config["DB_PATH"] = settings.DB_PATH

    cors_origins = settings.CORS_ORIGINS.split(",") if settings.CORS_ORIGINS != "*" else "*"
    CORS(app, origins=cors_origins)

    register_error_handlers(app)
    init_database(app)

    for bp in (home_bp, produto_bp, usuario_bp, pedido_bp, relatorio_bp, health_bp, admin_bp):
        app.register_blueprint(bp)

    return app
