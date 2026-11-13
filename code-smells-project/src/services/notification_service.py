import logging

log = logging.getLogger(__name__)


def pedido_criado(pedido_id, usuario_id):
    log.info("Enviando e-mail: pedido %s criado para usuário %s", pedido_id, usuario_id)
    log.info("Enviando SMS: seu pedido foi recebido!")
    log.info("Enviando push: novo pedido recebido pelo sistema")


def pedido_status_alterado(pedido_id, novo_status):
    if novo_status == "aprovado":
        log.info("Notificação: pedido %s foi aprovado! Preparar envio.", pedido_id)
    elif novo_status == "cancelado":
        log.info("Notificação: pedido %s cancelado. Devolver estoque.", pedido_id)
