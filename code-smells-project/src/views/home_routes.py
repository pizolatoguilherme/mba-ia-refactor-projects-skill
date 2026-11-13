from flask import Blueprint

from src.controllers import home_controller as c

home_bp = Blueprint("home", __name__)

home_bp.add_url_rule("/", "index", c.index, methods=["GET"])
