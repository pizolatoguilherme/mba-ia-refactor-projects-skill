from flask import Blueprint

from controllers import task_controller as controller

task_bp = Blueprint('tasks', __name__)

task_bp.add_url_rule('/tasks', 'get_tasks', controller.list_tasks, methods=['GET'])
task_bp.add_url_rule('/tasks/search', 'search_tasks', controller.search_tasks, methods=['GET'])
task_bp.add_url_rule('/tasks/stats', 'task_stats', controller.task_stats, methods=['GET'])
task_bp.add_url_rule('/tasks/<int:task_id>', 'get_task', controller.get_task, methods=['GET'])
task_bp.add_url_rule('/tasks', 'create_task', controller.create_task, methods=['POST'])
task_bp.add_url_rule('/tasks/<int:task_id>', 'update_task', controller.update_task, methods=['PUT'])
task_bp.add_url_rule('/tasks/<int:task_id>', 'delete_task', controller.delete_task, methods=['DELETE'])
