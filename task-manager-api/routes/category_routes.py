from flask import Blueprint

from controllers import category_controller as controller

category_bp = Blueprint('categories', __name__)

category_bp.add_url_rule('/categories', 'get_categories', controller.list_categories, methods=['GET'])
category_bp.add_url_rule('/categories', 'create_category', controller.create_category, methods=['POST'])
category_bp.add_url_rule('/categories/<int:cat_id>', 'update_category', controller.update_category, methods=['PUT'])
category_bp.add_url_rule('/categories/<int:cat_id>', 'delete_category', controller.delete_category, methods=['DELETE'])
