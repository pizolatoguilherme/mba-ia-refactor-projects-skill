from flask import jsonify

from src.services.relatorio_service import gerar_relatorio_vendas


def relatorio_vendas():
    relatorio = gerar_relatorio_vendas()
    return jsonify({"dados": relatorio, "sucesso": True}), 200
