from flask import Blueprint

from src.controllers import health_controller as c

health_bp = Blueprint("health", __name__)

health_bp.add_url_rule("/health", "health_check", c.health_check, methods=["GET"])
