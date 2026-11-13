from src.config.settings import FAIXAS_DESCONTO
from src.models import pedido_model


def calcular_desconto(faturamento):
    for limite, taxa in FAIXAS_DESCONTO:
        if faturamento > limite:
            return faturamento * taxa
    return 0.0


def gerar_relatorio_vendas():
    total_pedidos, faturamento = pedido_model.totais()
    desconto = calcular_desconto(faturamento)

    return {
        "total_pedidos": total_pedidos,
        "faturamento_bruto": round(faturamento, 2),
        "desconto_aplicavel": round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes": pedido_model.contagem_por_status("pendente"),
        "pedidos_aprovados": pedido_model.contagem_por_status("aprovado"),
        "pedidos_cancelados": pedido_model.contagem_por_status("cancelado"),
        "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
    }
