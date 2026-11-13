import os
import secrets
import logging

log = logging.getLogger(__name__)


def _bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")


class Settings:
    SECRET_KEY = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    DEBUG = _bool("FLASK_DEBUG", False)
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5000"))
    DB_PATH = os.environ.get("DB_PATH", "loja.db")
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")  # não definido => rotas /admin/* ficam bloqueadas
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")


if not os.environ.get("SECRET_KEY"):
    log.warning("SECRET_KEY não definida; usando uma chave efêmera gerada em memória")

# Constantes de negócio (antes espalhadas como literais em controllers.py/models.py)
CATEGORIAS_VALIDAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")
NOME_PRODUTO_MIN = 2
NOME_PRODUTO_MAX = 200

STATUS_PEDIDO_VALIDOS = ("pendente", "aprovado", "enviado", "entregue", "cancelado")
STATUS_PEDIDO_PADRAO = "pendente"

# (limite de faturamento, taxa de desconto) em ordem decrescente de limite
FAIXAS_DESCONTO = ((10000, 0.10), (5000, 0.05), (1000, 0.02))

TIPO_USUARIO_PADRAO = "cliente"
