import logging

log = logging.getLogger(__name__)


def pedido_criado(pedido_id, usuario_id):
    log.info("ENVIANDO EMAIL: Pedido %s criado para usuario %s", pedido_id, usuario_id)
    log.info("ENVIANDO SMS: Seu pedido foi recebido!")
    log.info("ENVIANDO PUSH: Novo pedido recebido pelo sistema")


def pedido_status_alterado(pedido_id, novo_status):
    if novo_status == "aprovado":
        log.info("NOTIFICAÇÃO: Pedido %s foi aprovado! Preparar envio.", pedido_id)
    if novo_status == "cancelado":
        log.info("NOTIFICAÇÃO: Pedido %s cancelado. Devolver estoque.", pedido_id)
