from flask import Blueprint

from src.controllers import admin_controller as c
from src.middlewares.admin_auth import require_admin

admin_bp = Blueprint("admin", __name__)

admin_bp.add_url_rule(
    "/admin/reset-db", "reset_database", require_admin(c.reset_database), methods=["POST"]
)
admin_bp.add_url_rule(
    "/admin/query", "executar_query", require_admin(c.executar_query), methods=["POST"]
)
