import logging
from datetime import datetime

from flask import Flask
from flask_cors import CORS

from config.settings import Settings
from database import db
from middlewares.error_handler import register_error_handlers
from routes.task_routes import task_bp
from routes.user_routes import user_bp
from routes.category_routes import category_bp
from routes.report_routes import report_bp


def create_app(settings=Settings):
    app = Flask(__name__)
    app.config.from_object(settings)

    CORS(app, origins=settings.CORS_ORIGINS)
    db.init_app(app)
    register_error_handlers(app)

    for bp in (task_bp, user_bp, category_bp, report_bp):
        app.register_blueprint(bp)

    @app.route('/health')
    def health():
        return {'status': 'ok', 'timestamp': str(datetime.now())}

    @app.route('/')
    def index():
        return {'message': 'Task Manager API', 'version': '1.0'}

    with app.app_context():
        db.create_all()

    return app


logging.basicConfig(level=logging.INFO)
app = create_app()  # mantido em nível de módulo: seed.py faz `from app import app, db`

if __name__ == '__main__':
    app.run(debug=Settings.DEBUG, host=Settings.HOST, port=Settings.PORT)
