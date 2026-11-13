from flask import current_app, jsonify

from src.models import pedido_model, produto_model, usuario_model


def health_check():
    ambiente = "desenvolvimento" if current_app.config.get("DEBUG") else "producao"
    return jsonify(
        {
            "status": "ok",
            "database": "connected",
            "counts": {
                "produtos": produto_model.count(),
                "usuarios": usuario_model.count(),
                "pedidos": pedido_model.count(),
            },
            "versao": "1.0.0",
            "ambiente": ambiente,
        }
    ), 200
