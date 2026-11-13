import logging

from flask import jsonify, request

from src.database import get_db
from src.middlewares.error_handler import ValidationError

log = logging.getLogger(__name__)


def reset_database():
    db = get_db()
    db.execute("DELETE FROM itens_pedido")
    db.execute("DELETE FROM pedidos")
    db.execute("DELETE FROM produtos")
    db.execute("DELETE FROM usuarios")
    db.commit()
    log.warning("Banco de dados resetado via /admin/reset-db")
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200


def executar_query():
    dados = request.get_json(silent=True) or {}
    query = dados.get("sql", "")
    if not query:
        raise ValidationError("Query não informada")

    db = get_db()
    cursor = db.execute(query)
    if query.strip().upper().startswith("SELECT"):
        rows = cursor.fetchall()
        resultado = [dict(row) for row in rows]
        return jsonify({"dados": resultado, "sucesso": True}), 200

    db.commit()
    return jsonify({"mensagem": "Query executada", "sucesso": True}), 200
